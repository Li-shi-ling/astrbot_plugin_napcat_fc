from __future__ import annotations

from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.star import Context, Star, register

from napcat_fc.registry import build_endpoint_tools, discover_all_endpoint_specs
from napcat_fc.tools import build_generic_call_tool


@register(
    "astrbot_plugin_napcat_fc",
    "Soulter / AstrBot contributors",
    "将 NapCat / OneBot HTTP API 暴露为 AstrBot LLM 函数工具。",
    "1.5.0",
)
class NapCatFunctionToolsPlugin(Star):
    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        super().__init__(context)
        self.config = dict(config or {})
        self.plugin_dir = Path(__file__).resolve().parent

        specs = discover_all_endpoint_specs(self.plugin_dir)
        tools = build_endpoint_tools(
            specs=specs,
            tool_prefix=str(self.config.get("tool_prefix") or "napcat"),
        )

        if self.config.get("enable_generic_tool", True):
            tools.append(
                build_generic_call_tool(
                    tool_name=f"{self.config.get('tool_prefix') or 'napcat'}_call_api",
                )
            )

        if self.config.get("register_tools", True):
            self.context.add_llm_tools(*tools)
            for tool in tools:
                tool.handler_module_path = __name__
            logger.info(f"NapCat 函数工具已注册：{len(tools)} 个。")
        else:
            logger.info("NapCat 函数工具注册已被配置关闭。")

        self.tools = tools

    async def initialize(self):
        logger.info("NapCat 函数工具插件初始化完成。")

    async def terminate(self):
        return None
