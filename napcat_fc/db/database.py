from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel


class ToolDBManager:
    """Async SQLite manager for NapCat tool discovery metadata."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self.db_url = f"sqlite+aiosqlite:///{db_path}"
        self.engine = create_async_engine(
            self.db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.async_session_factory = self.async_session
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def init_db(self):
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            await self._init_db_once()
            self._initialized = True

    async def _init_db_once(self):
        async with self.engine.begin() as conn:
            try:
                await conn.run_sync(
                    lambda sync_conn: SQLModel.metadata.create_all(
                        sync_conn, tables=list(self._get_plugin_tables().values())
                    )
                )
            except OperationalError as exc:
                if "already exists" not in str(exc):
                    raise

        async with self.engine.connect() as conn:
            await self._ensure_table_columns(conn)
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA cache_size=-20000"))
            await conn.execute(text("PRAGMA temp_store=MEMORY"))
            await conn.execute(text("PRAGMA optimize"))
            await conn.commit()

        await self.validate_db()

    async def _ensure_table_columns(self, conn):
        from .tables import NapcatToolRecord

        expected_columns = NapcatToolRecord.__table__.columns
        result = await conn.execute(text('PRAGMA table_info("napcat_tool")'))
        existing_columns = {str(row[1]) for row in result.fetchall() if len(row) > 1}
        for column in expected_columns:
            if column.name in existing_columns:
                continue
            await conn.execute(
                text(
                    f'ALTER TABLE "napcat_tool" ADD COLUMN '
                    f'"{column.name}" {self._sqlite_column_definition(column)}'
                )
            )

    def _sqlite_column_definition(self, column) -> str:
        try:
            python_type = column.type.python_type
        except NotImplementedError:
            python_type = str
        if python_type is bool:
            column_type = "BOOLEAN"
            default_value = column.default.arg if column.default is not None else False
            default = f" DEFAULT {1 if default_value is True else 0}"
        else:
            column_type = "VARCHAR"
            default_value = column.default.arg if column.default is not None else None
            if default_value is None:
                default = " DEFAULT ''"
            else:
                escaped = str(default_value).replace("'", "''")
                default = f" DEFAULT '{escaped}'"
        return f"{column_type} NOT NULL{default}"

    async def validate_db(self):
        expected_tables = {
            table_name: set(table.columns.keys())
            for table_name, table in self._get_plugin_tables().items()
        }

        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
            existing_tables = {str(row[0]) for row in result.fetchall()}
            missing_tables = sorted(set(expected_tables) - existing_tables)
            if missing_tables:
                raise RuntimeError(
                    "工具管理数据库缺少数据表: " + ", ".join(missing_tables)
                )

            missing_columns: dict[str, list[str]] = {}
            for table_name, expected_columns in expected_tables.items():
                pragma_result = await conn.execute(
                    text(f'PRAGMA table_info("{table_name}")')
                )
                existing_columns = {
                    str(row[1]) for row in pragma_result.fetchall() if len(row) > 1
                }
                table_missing_columns = sorted(expected_columns - existing_columns)
                if table_missing_columns:
                    missing_columns[table_name] = table_missing_columns

            if missing_columns:
                parts = [
                    f"{table_name} 缺少字段: {', '.join(columns)}"
                    for table_name, columns in missing_columns.items()
                ]
                raise RuntimeError("工具管理数据库结构不完整: " + "; ".join(parts))

    def _get_plugin_tables(self):
        from . import tables

        return {
            tables.NapcatToolRecord.__table__.name: tables.NapcatToolRecord.__table__,
            tables.NapcatDiscoveredToolRecord.__table__.name: tables.NapcatDiscoveredToolRecord.__table__,
        }

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        session = self.async_session_factory()
        try:
            async with session.begin():
                yield session
        finally:
            await session.close()

    async def close(self):
        await self.engine.dispose()
