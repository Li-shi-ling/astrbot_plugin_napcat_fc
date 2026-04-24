from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class NapcatToolRecord(SQLModel, table=True):
    """Persisted metadata for an AstrBot LLM tool backed by NapCat."""

    __tablename__ = "napcat_tool"
    __table_args__ = {"extend_existing": True}

    tool_name: str = Field(primary_key=True, index=True, description="工具名")
    endpoint: str = Field(index=True, description="NapCat/OneBot API")
    method_name: str = Field(index=True, description="插件方法名")
    capability: str = Field(default="", index=True, description="工具能力")
    parameters_json: str = Field(default="[]", description="参数 JSON")
    required_parameters_json: str = Field(default="[]", description="必填参数 JSON")
    platforms_json: str = Field(default="[]", description="限定平台 JSON")
    enabled: bool = Field(default=True, index=True, description="是否启用")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
