from __future__ import annotations

from typing import Any

from astrbot.api import FunctionTool

from napcat_fc.client import NapCatClient


PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "payload": {
            "type": "object",
            "description": "OneBot/NapCat 接口请求体。字段名必须与接口文档一致。",
            "additionalProperties": True,
        }
    },
    "required": ["payload"],
}


def build_endpoint_tool(
    client: NapCatClient,
    spec: Any,
    tool_name: str,
) -> FunctionTool:
    async def handler(_event, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ValueError("payload 必须是对象。")
        return await client.request(spec.endpoint, payload)

    return FunctionTool(
        name=tool_name,
        description=(
            f"调用 NapCat/OneBot 接口 /{spec.endpoint}。"
            f"用途：{spec.title}。请求参数放入 payload，字段以本地文档 {spec.source} 为准。"
        ),
        parameters=PAYLOAD_SCHEMA,
        handler=handler,
    )


def build_generic_call_tool(
    client: NapCatClient,
    tool_name: str = "napcat_call_api",
) -> FunctionTool:
    async def handler(_event, endpoint: str, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ValueError("payload 必须是对象。")
        return await client.request(endpoint, payload)

    return FunctionTool(
        name=tool_name,
        description="调用任意 NapCat/OneBot HTTP API。endpoint 填接口名或路径，payload 填请求体。",
        parameters={
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "接口名或路径，例如 send_group_msg 或 /send_group_msg。",
                },
                "payload": {
                    "type": "object",
                    "description": "接口请求体对象。",
                    "additionalProperties": True,
                },
            },
            "required": ["endpoint", "payload"],
        },
        handler=handler,
    )
