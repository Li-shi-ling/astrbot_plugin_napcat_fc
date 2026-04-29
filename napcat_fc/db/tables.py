from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class NapcatToolRecord(SQLModel, table=True):
    """Persisted metadata for an AstrBot LLM tool backed by NapCat."""

    __tablename__ = "napcat_tool"
    __table_args__ = {"extend_existing": True}

    tool_name: str = Field(primary_key=True, index=True, description="tool name")
    endpoint: str = Field(index=True, description="NapCat/OneBot API")
    method_name: str = Field(index=True, description="plugin method name")
    capability: str = Field(default="", index=True, description="tool capability")
    namespace: str = Field(default="", index=True, description="tool namespace")
    aliases_json: str = Field(default="[]", description="search aliases JSON")
    risk_level: str = Field(default="low", index=True, description="risk level")
    requires_confirmation: bool = Field(
        default=False,
        description="whether confirmation is required",
    )
    default_discoverable: bool = Field(
        default=True,
        index=True,
        description="whether discoverable by default",
    )
    parameters_json: str = Field(default="[]", description="parameters JSON")
    required_parameters_json: str = Field(default="[]", description="required parameters JSON")
    platforms_json: str = Field(default="[]", description="platforms JSON")
    enabled: bool = Field(default=True, index=True, description="enabled")
    updated_at: datetime = Field(default_factory=datetime.now, description="updated at")
