from __future__ import annotations

from pathlib import Path

import pytest

import astrbot.api  # noqa: F401
from astrbot.core.platform.astrbot_message import AstrBotMessage
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from main import NapCatFunctionToolsPlugin
from napcat_fc.registry import discover_all_endpoint_specs, discover_endpoint_specs, make_tool_name


class FakeApi:
    def __init__(self):
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        return {"status": "ok", "data": payload}


class FakeBot:
    def __init__(self):
        self.api = FakeApi()


def make_aiocqhttp_event():
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE
    message.message = []
    message.message_str = ""
    message.sender = None
    message.self_id = "10000"
    message.message_id = "1"
    message.session_id = "123456"
    message.raw_message = None
    return AiocqhttpMessageEvent(
        message_str="",
        message_obj=message,
        platform_meta=PlatformMetadata(
            name="aiocqhttp",
            description="aiocqhttp",
            id="aiocqhttp",
        ),
        session_id="123456",
        bot=FakeBot(),
    )


def test_discover_endpoint_specs_finds_napcat_docs():
    specs = discover_endpoint_specs(
        Path(__file__).resolve().parents[1] / "docs" / "napcat-apifox"
    )

    endpoints = {spec.endpoint for spec in specs}
    assert "send_group_msg" in endpoints
    assert "send_private_msg" in endpoints
    assert "get_group_list" in endpoints
    assert len(endpoints) >= 100


def test_main_registers_explicit_llm_tool_decorators():
    plugin_dir = Path(__file__).resolve().parents[1]
    specs = discover_all_endpoint_specs(plugin_dir)
    source = (plugin_dir / "main.py").read_text(encoding="utf-8")

    assert source.count("@filter.llm_tool") == len(specs) + 1
    assert '@filter.llm_tool(name="napcat_call_api")' in source
    assert "@filter.llm_tool(name='napcat_send_group_msg')" in source
    assert "@filter.llm_tool(name='napcat_send_private_msg')" in source
    assert "@filter.llm_tool(name='napcat_set_group_anonymous_ban')" in source


@pytest.mark.asyncio
async def test_endpoint_tool_calls_expected_endpoint():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_group_msg_tool(
        event, {"group_id": "123", "message": "hello"}
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        ("send_group_msg", {"group_id": "123", "message": "hello"})
    ]


@pytest.mark.asyncio
async def test_generic_tool_calls_expected_endpoint():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_call_api_tool(event, "get_group_list", {})

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [("get_group_list", {})]


@pytest.mark.asyncio
async def test_aiocqhttp_action_rejects_non_aiocqhttp_event():
    plugin = NapCatFunctionToolsPlugin(context=None)

    with pytest.raises(ValueError, match="aiocqhttp/NapCat"):
        await plugin._call_napcat_api(object(), "get_group_list", {})


@pytest.mark.asyncio
async def test_aiocqhttp_action_accepts_slash_endpoint():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin._call_napcat_api(event, "/send_msg", {"message": "hello"})

    assert event.bot.api.calls == [("send_msg", {"message": "hello"})]


def test_tool_name_keeps_internal_dot_endpoint_distinct():
    assert make_tool_name("napcat", ".ocr_image") == "napcat_dot_ocr_image"
    assert make_tool_name("napcat", "ocr_image") == "napcat_ocr_image"
