from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select

from .database import ToolDBManager
from .tables import NapcatToolRecord


@dataclass(frozen=True)
class ToolRegistryData:
    tool_name: str
    endpoint: str
    method_name: str
    capability: str
    parameters_json: str
    required_parameters_json: str
    platforms_json: str
    enabled: bool = True


class ToolRegistryRepo:
    """Repository for dynamic LLM tool discovery metadata."""

    def __init__(self, db_manager: ToolDBManager):
        self.db = db_manager

    async def sync_tools(self, tools: list[ToolRegistryData]) -> int:
        async with self.db.get_session() as session:
            result = await session.execute(select(NapcatToolRecord))
            existing_by_name = {
                record.tool_name: record for record in result.scalars().all()
            }
            incoming_names = {tool.tool_name for tool in tools}

            for tool_name, existing in existing_by_name.items():
                if tool_name not in incoming_names:
                    await session.delete(existing)

            for tool in tools:
                existing = existing_by_name.get(tool.tool_name)
                enabled = existing.enabled if existing else tool.enabled
                if existing:
                    existing.endpoint = tool.endpoint
                    existing.method_name = tool.method_name
                    existing.capability = tool.capability
                    existing.parameters_json = tool.parameters_json
                    existing.required_parameters_json = tool.required_parameters_json
                    existing.platforms_json = tool.platforms_json
                    existing.enabled = enabled
                    existing.updated_at = datetime.now()
                else:
                    session.add(self._to_record(tool))
            return len(tools)

    async def replace_all_tools(self, tools: list[ToolRegistryData]) -> int:
        async with self.db.get_session() as session:
            await session.execute(delete(NapcatToolRecord))
            for tool in tools:
                session.add(self._to_record(tool))
            return len(tools)

    async def upsert_tools(self, tools: list[ToolRegistryData]) -> int:
        async with self.db.get_session() as session:
            for tool in tools:
                existing = await session.get(NapcatToolRecord, tool.tool_name)
                if existing:
                    existing.endpoint = tool.endpoint
                    existing.method_name = tool.method_name
                    existing.capability = tool.capability
                    existing.parameters_json = tool.parameters_json
                    existing.required_parameters_json = tool.required_parameters_json
                    existing.platforms_json = tool.platforms_json
                    existing.enabled = tool.enabled
                    existing.updated_at = datetime.now()
                else:
                    session.add(self._to_record(tool))
            return len(tools)

    async def get_tool(self, tool_name: str) -> NapcatToolRecord | None:
        async with self.db.get_session() as session:
            return await session.get(NapcatToolRecord, tool_name)

    async def list_tools(
        self,
        *,
        enabled_only: bool = False,
        platform: str | None = None,
    ) -> list[NapcatToolRecord]:
        async with self.db.get_session() as session:
            stmt = select(NapcatToolRecord)
            if enabled_only:
                stmt = stmt.where(NapcatToolRecord.enabled.is_(True))
            stmt = stmt.order_by(NapcatToolRecord.tool_name.asc())
            result = await session.execute(stmt)
            records = list(result.scalars().all())

        if platform is None:
            return records

        normalized = platform.strip().lower()
        if not normalized:
            return records
        return [
            record
            for record in records
            if record.platforms_json == "[]"
            or f'"{normalized}"' in record.platforms_json
        ]

    async def set_tool_enabled(self, tool_name: str, enabled: bool) -> bool:
        async with self.db.get_session() as session:
            record = await session.get(NapcatToolRecord, tool_name)
            if record is None:
                return False
            record.enabled = enabled
            record.updated_at = datetime.now()
            return True

    def _to_record(self, tool: ToolRegistryData) -> NapcatToolRecord:
        return NapcatToolRecord(
            tool_name=tool.tool_name,
            endpoint=tool.endpoint,
            method_name=tool.method_name,
            capability=tool.capability,
            parameters_json=tool.parameters_json,
            required_parameters_json=tool.required_parameters_json,
            platforms_json=tool.platforms_json,
            enabled=tool.enabled,
            updated_at=datetime.now(),
        )
