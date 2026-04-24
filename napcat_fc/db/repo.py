from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, or_, select

from .database import ToolDBManager
from .tables import NapcatDiscoveredToolRecord, NapcatToolRecord


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

    async def search_tools(
        self,
        keyword: str,
        *,
        limit: int = 3,
        enabled_only: bool = True,
    ) -> list[NapcatToolRecord]:
        normalized = keyword.strip().lower()
        if not normalized:
            return []

        pattern = f"%{normalized}%"
        stmt = select(NapcatToolRecord).where(
            or_(
                func.lower(NapcatToolRecord.tool_name).like(pattern),
                func.lower(NapcatToolRecord.endpoint).like(pattern),
                func.lower(NapcatToolRecord.capability).like(pattern),
                func.lower(NapcatToolRecord.parameters_json).like(pattern),
            )
        )
        if enabled_only:
            stmt = stmt.where(NapcatToolRecord.enabled.is_(True))

        async with self.db.get_session() as session:
            result = await session.execute(stmt)
            records = list(result.scalars().all())

        return sorted(
            records,
            key=lambda record: (
                -self._search_score(record, normalized),
                record.tool_name,
            ),
        )[: max(0, limit)]

    async def list_discovered_tool_names(self) -> list[str]:
        async with self.db.get_session() as session:
            result = await session.execute(
                select(NapcatDiscoveredToolRecord).order_by(
                    NapcatDiscoveredToolRecord.position.asc()
                )
            )
            return [record.tool_name for record in result.scalars().all()]

    async def add_discovered_tool_names(
        self,
        tool_names: list[str],
        *,
        max_size: int = 20,
    ) -> list[str]:
        existing = await self.list_discovered_tool_names()
        queue = list(existing)
        for tool_name in tool_names:
            if tool_name in queue:
                queue.remove(tool_name)
            queue.append(tool_name)
        if max_size > 0 and len(queue) > max_size:
            queue = queue[-max_size:]
        await self.replace_discovered_tool_names(queue)
        return queue

    async def replace_discovered_tool_names(self, tool_names: list[str]) -> int:
        async with self.db.get_session() as session:
            await session.execute(delete(NapcatDiscoveredToolRecord))
            for index, tool_name in enumerate(dict.fromkeys(tool_names)):
                session.add(
                    NapcatDiscoveredToolRecord(
                        tool_name=tool_name,
                        position=index,
                        updated_at=datetime.now(),
                    )
                )
            return len(tool_names)

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

    def _search_score(self, record: NapcatToolRecord, keyword: str) -> int:
        score = 0
        tool_name = record.tool_name.lower()
        endpoint = record.endpoint.lower()
        capability = record.capability.lower()
        params = record.parameters_json.lower()
        if tool_name == keyword or endpoint == keyword:
            score += 100
        if tool_name.startswith(keyword) or endpoint.startswith(keyword):
            score += 50
        if keyword in tool_name:
            score += 30
        if keyword in endpoint:
            score += 25
        if keyword in capability:
            score += 20
        if keyword in params:
            score += 5
        return score
