from __future__ import annotations

import json
import importlib.util
import inspect
import re
import sqlite3
import subprocess
import sys
import asyncio
import uuid
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import astrbot.api  # noqa: F401
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.message.components import Image, Reply
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.agent.tool import FunctionTool, ToolSet
from astrbot.core.provider.entities import ProviderRequest

import main as napcat_plugin_main
from main import NapCatFunctionToolsPlugin
from napcat_fc.db import ToolDBManager, ToolRegistryRepo
from napcat_fc.registry import discover_all_endpoint_specs, discover_endpoint_specs, make_tool_name
from napcat_fc.tool_registry import build_tool_registry_data


class FakeApi:
    def __init__(self):
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        return {"status": "ok", "data": payload}


class NullApi:
    def __init__(self):
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        return None


class FakeBot:
    def __init__(self):
        self.api = FakeApi()


class SlowApi:
    def __init__(self, delay: float):
        self.delay = delay
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        await asyncio.sleep(self.delay)
        return {"status": "ok", "data": payload}


class FailingApi:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        raise self.error


class ArkApi:
    def __init__(self, ark_data='{"app":"com.tencent.contact.lua"}', direct_ark=False):
        self.ark_data = ark_data
        self.direct_ark = direct_ark
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        if action in {"ArkShareGroup", "ArkSharePeer", "send_ark_share", "send_group_ark_share"}:
            if self.direct_ark:
                return self.ark_data
            return {"status": "ok", "data": self.ark_data}
        return {"status": "ok", "data": payload}


class FakeToolManager:
    def __init__(self, tools):
        self.func_list = list(tools)

    def get_func(self, name):
        for tool in reversed(self.func_list):
            if tool.name == name:
                return tool
        return None

    def spec_to_func(self, name, func_args, desc, handler):
        parameters = {"type": "object", "properties": {}}
        for arg in func_args:
            arg = dict(arg)
            arg_name = arg.pop("name")
            parameters["properties"][arg_name] = arg
        return FunctionTool(
            name=name,
            description=desc,
            parameters=parameters,
            handler=handler,
        )

    def add_func(self, name, func_args, desc, handler):
        self.remove_func(name)
        self.func_list.append(self.spec_to_func(name, func_args, desc, handler))

    def remove_func(self, name):
        for index, tool in enumerate(self.func_list):
            if tool.name == name:
                self.func_list.pop(index)
                break


class FakeContext:
    def __init__(self, tools):
        self.tool_manager = FakeToolManager(tools)

    def get_llm_tool_manager(self):
        return self.tool_manager


def make_aiocqhttp_event(
    *,
    group_id: str | None = None,
    user_id: str = "123456",
    message_id: str = "1",
    message_components: list | None = None,
    raw_message=None,
    message_str: str = "",
):
    message = AstrBotMessage()
    message.type = MessageType.GROUP_MESSAGE if group_id else MessageType.FRIEND_MESSAGE
    message.message = list(message_components or [])
    message.message_str = message_str
    message.sender = MessageMember(user_id=user_id, nickname="tester")
    message.self_id = "10000"
    message.message_id = message_id
    message.group_id = group_id
    message.session_id = group_id or user_id
    message.raw_message = raw_message
    return AiocqhttpMessageEvent(
        message_str=message_str,
        message_obj=message,
        platform_meta=PlatformMetadata(
            name="aiocqhttp",
            description="aiocqhttp",
            id="aiocqhttp",
        ),
        session_id=group_id or user_id,
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


def test_only_search_and_call_tools_use_llm_tool_decorator_and_api_tools_use_markers():
    plugin_dir = Path(__file__).resolve().parents[1]
    source = (plugin_dir / "main.py").read_text(encoding="utf-8")

    assert source.count("@filter.llm_tool") == 2
    assert "@filter.llm_tool(name='napcat_search_tools')" in source
    assert "@filter.llm_tool(name='napcat_call_tool')" in source
    assert source.count("# napcat_tool:") == 160
    assert "napcat_call_api" not in source
    assert "# napcat_tool: napcat_send_msg" in source
    assert "# napcat_tool: napcat_send_group_msg" not in source
    assert "# napcat_tool: napcat_send_private_msg" not in source
    assert "# napcat_tool: napcat_set_group_anonymous_ban" in source
    send_msg_signature = source.split("async def napcat_send_msg_tool(", 1)[1].split("):", 1)[0]
    assert "payload" not in send_msg_signature
    assert "group_id: " in source
    assert "message: " in source


def test_main_can_load_internal_package_from_astrbot_root():
    plugin_dir = Path(__file__).resolve().parents[1]
    main_path = plugin_dir / "main.py"
    script = f"""
import importlib.util
import sys
from pathlib import Path

plugin_dir = Path(r"{plugin_dir}")
main_path = Path(r"{main_path}")
sys.path = [path for path in sys.path if path != str(plugin_dir)]
spec = importlib.util.spec_from_file_location("isolated_napcat_plugin", main_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.NapCatFunctionToolsPlugin.__name__ == "NapCatFunctionToolsPlugin"
assert str(plugin_dir) in sys.path
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=plugin_dir.parent.parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_platform_tool_name_class_attributes_only_record_os_specific_tools():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    registered_names = tuple(re.findall(r"# napcat_tool:\s*([a-zA-Z0-9_]+)", source))

    assert NapCatFunctionToolsPlugin.WINDOWS_TOOL_NAMES == (
        "napcat_dot_ocr_image",
        "napcat_ocr_image",
    )
    assert NapCatFunctionToolsPlugin.LINUX_TOOL_NAMES == ()
    assert NapCatFunctionToolsPlugin.MAC_TOOL_NAMES == ()
    assert set(NapCatFunctionToolsPlugin.WINDOWS_TOOL_NAMES).issubset(registered_names)
    assert "仅 Windows 可用" in source


@pytest.mark.asyncio
async def test_endpoint_tool_calls_expected_endpoint():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_msg_tool(
        event,
        group_id=123456,
        message="hello",
        message_type="group",
        auto_escape=False,
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_msg",
            {
                "group_id": 123456,
                "message": "hello",
                "message_type": "group",
                "auto_escape": False,
                "user_id": 123456,
            },
        )
    ]


def test_context_defaults_fill_values_from_aiocqhttp_event():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456", message_id="789")
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {
        "group_id": None,
        "user_id": None,
        "self_id": None,
        "message_id": None,
    }

    assert plugin._fill_context_defaults(event, payload) is None

    assert payload == {
        "group_id": 654321,
        "user_id": 123456,
        "self_id": 10000,
        "message_id": 789,
    }


def test_context_defaults_treat_zero_and_blank_as_current_context_markers():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456", message_id="789")
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {
        "group_id": 0,
        "user_id": "0",
        "self_id": "",
        "message_id": " ",
    }

    assert plugin._fill_context_defaults(event, payload) is None

    assert payload == {
        "group_id": 654321,
        "user_id": 123456,
        "self_id": 10000,
        "message_id": 789,
    }


def test_context_defaults_fallback_invalid_short_ids_and_warn(monkeypatch):
    warnings = []
    monkeypatch.setattr("main.logger.warning", warnings.append)
    event = make_aiocqhttp_event(group_id="654321", user_id="123456", message_id="789")
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {
        "group_id": "12345",
        "user_id": "not-a-number",
        "self_id": 123,
    }

    assert plugin._fill_context_defaults(event, payload) is None

    assert payload == {
        "group_id": 654321,
        "user_id": 123456,
        "self_id": 10000,
    }
    assert len(warnings) == 3
    assert all("已回退为当前会话默认值" in item for item in warnings)


def test_context_defaults_fallback_group_id_when_user_id_is_misused(monkeypatch):
    warnings = []
    monkeypatch.setattr("main.logger.warning", warnings.append)
    event = make_aiocqhttp_event(group_id="654321", user_id="123456", message_id="789")
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {"group_id": 123456}

    assert plugin._fill_context_defaults(event, payload) is None

    assert payload == {"group_id": 654321}
    assert warnings == [
        "NapCat 工具参数 group_id 等于当前消息发送者 user_id，疑似把用户号误填为群号，已回退为当前群号。"
    ]


def test_context_defaults_can_disable_invalid_short_id_fallback(monkeypatch):
    warnings = []
    monkeypatch.setattr("main.logger.warning", warnings.append)
    event = make_aiocqhttp_event(group_id="654321", user_id="123456", message_id="789")
    plugin = NapCatFunctionToolsPlugin(
        context=None,
        config={"fallback_invalid_context_ids": False},
    )
    payload = {
        "group_id": "12345",
        "user_id": "not-a-number",
        "self_id": 123,
    }

    assert plugin._fill_context_defaults(event, payload) is None

    assert payload == {
        "group_id": "12345",
        "user_id": "not-a-number",
        "self_id": 123,
    }
    assert warnings == []


def test_message_id_default_prefers_reply_component_then_current_message():
    event = make_aiocqhttp_event(
        group_id="654321",
        message_id="789",
        message_components=[Reply(id="456")],
    )
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {"message_id": None}

    assert plugin._fill_context_defaults(event, payload) is None
    assert payload["message_id"] == 456

    event.message_obj.message = []
    payload = {"message_id": None}

    assert plugin._fill_context_defaults(event, payload) is None
    assert payload["message_id"] == 789


def test_message_id_default_reads_raw_onebot_reply_segment():
    raw_message = SimpleNamespace(
        message=[
            {"type": "reply", "data": {"id": "456"}},
            {"type": "text", "data": {"text": "设置待办"}},
        ]
    )
    event = make_aiocqhttp_event(
        group_id="654321",
        message_id="789",
        raw_message=raw_message,
    )
    plugin = NapCatFunctionToolsPlugin(context=None)
    payload = {"message_id": None}

    assert plugin._fill_context_defaults(event, payload) is None
    assert payload["message_id"] == 456


@pytest.mark.asyncio
async def test_group_context_default_returns_friendly_message_in_private_chat():
    event = make_aiocqhttp_event(user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin._call_napcat_api(
        event,
        "send_group_msg",
        {"group_id": None, "message": "hello"},
    )
    payload = json.loads(result)

    assert payload["status"] == "missing_context"
    assert "当前消息不是群聊事件" in payload["message"]
    assert "group_id" in payload["message"]
    assert event.bot.api.calls == []


@pytest.mark.asyncio
async def test_group_tool_uses_current_group_when_group_id_is_omitted():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_send_msg_tool(event, message="hello", message_type="group")

    assert event.bot.api.calls == [
        (
            "send_msg",
            {
                "group_id": 654321,
                "message": "hello",
                "message_type": "group",
                "user_id": 123456,
            },
        )
    ]


@pytest.mark.asyncio
async def test_group_todo_uses_replied_message_id_when_message_id_is_omitted():
    event = make_aiocqhttp_event(
        group_id="654321",
        user_id="123456",
        message_id="789",
        message_components=[Reply(id="456")],
    )
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_set_group_todo_tool(event)

    assert event.bot.api.calls == [
        (
            "set_group_todo",
            {"group_id": 654321, "message_id": 456},
        )
    ]


@pytest.mark.asyncio
async def test_album_upload_uses_replied_image_when_file_is_omitted():
    event = make_aiocqhttp_event(
        group_id="654321",
        message_components=[
            Reply(
                id="456",
                chain=[
                    Image(file="reply-file.jpg", url="https://example.com/reply.jpg")
                ],
            ),
            Image(file="current-file.jpg", url="https://example.com/current.jpg"),
        ],
    )
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_upload_image_to_qun_album_tool(
        event,
        album_id="album_1",
        album_name="测试相册",
    )

    assert event.bot.api.calls == [
        (
            "upload_image_to_qun_album",
            {
                "album_id": "album_1",
                "album_name": "测试相册",
                "file": "https://example.com/reply.jpg",
                "group_id": 654321,
            },
        )
    ]


@pytest.mark.asyncio
async def test_album_upload_falls_back_to_current_image_when_no_reply_image():
    event = make_aiocqhttp_event(
        group_id="654321",
        message_components=[
            Image(file="current-file.jpg", url="https://example.com/current.jpg"),
        ],
    )
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_upload_image_to_qun_album_tool(
        event,
        album_id="album_1",
        album_name="测试相册",
    )

    assert event.bot.api.calls == [
        (
            "upload_image_to_qun_album",
            {
                "album_id": "album_1",
                "album_name": "测试相册",
                "file": "https://example.com/current.jpg",
                "group_id": 654321,
            },
        )
    ]


@pytest.mark.asyncio
async def test_album_upload_returns_friendly_message_when_file_is_missing():
    event = make_aiocqhttp_event(group_id="654321")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_upload_image_to_qun_album_tool(
        event,
        album_id="album_1",
        album_name="测试相册",
    )
    payload = json.loads(result)

    assert payload["status"] == "missing_context"
    assert "图片" in payload["message"]
    assert event.bot.api.calls == []


@pytest.mark.asyncio
async def test_send_poke_maps_target_id_to_user_id_and_uses_current_group():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_poke_tool(event, target_id=3209552419)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_poke",
            {"user_id": 3209552419, "group_id": 654321},
        )
    ]


@pytest.mark.asyncio
async def test_send_poke_defaults_to_current_sender_in_private_chat():
    event = make_aiocqhttp_event(user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_poke_tool(event)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [("send_poke", {"user_id": 123456})]


@pytest.mark.asyncio
async def test_send_like_defaults_times_to_one_when_argument_missing():
    event = make_aiocqhttp_event(user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_like_tool(event)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        ("send_like", {"times": 1, "user_id": 123456})
    ]


@pytest.mark.asyncio
async def test_friend_poke_maps_target_id_and_uses_current_group_when_available():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_friend_poke_tool(event, target_id=3209552419)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "friend_poke",
            {"user_id": 3209552419, "group_id": 654321},
        )
    ]


@pytest.mark.asyncio
async def test_group_poke_maps_target_id_to_user_id_and_uses_current_group():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_group_poke_tool(event, target_id=3209552419)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "group_poke",
            {"group_id": 654321, "user_id": 3209552419},
        )
    ]


@pytest.mark.asyncio
async def test_optional_group_and_user_params_are_filled_for_group_context():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_forward_msg_tool(
        event,
        message="hello",
        messages=[],
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_group_forward_msg",
            {
                "message": "hello",
                "messages": [],
                "group_id": 654321,
            },
        )
    ]


@pytest.mark.asyncio
async def test_optional_group_and_user_params_only_fill_user_in_private_context():
    event = make_aiocqhttp_event(user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_forward_msg_tool(
        event,
        message="hello",
        messages=[],
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_private_forward_msg",
            {"message": "hello", "messages": [], "user_id": 123456},
        )
    ]


@pytest.mark.asyncio
async def test_send_forward_msg_builds_nodes_from_message_ids_and_uses_current_group():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_forward_msg_tool(
        event,
        message_ids=[111, "222"],
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_group_forward_msg",
            {
                "messages": [
                    {"type": "node", "data": {"id": 111}},
                    {"type": "node", "data": {"id": 222}},
                ],
                "group_id": 654321,
            },
        )
    ]


@pytest.mark.asyncio
async def test_get_msg_history_routes_to_group_or_private_history():
    group_event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_get_msg_history_tool(group_event, count=10)

    assert group_event.bot.api.calls == [
        (
            "get_group_msg_history",
            {
                "count": 10,
                "disable_get_url": True,
                "parse_mult_msg": True,
                "quick_reply": True,
                "reverse_order": True,
                "reverseOrder": True,
                "message_seq": 0,
                "group_id": 654321,
            },
        )
    ]

    private_event = make_aiocqhttp_event(user_id="123456")
    await plugin.napcat_get_msg_history_tool(private_event, count=5)

    assert private_event.bot.api.calls == [
        (
            "get_friend_msg_history",
            {
                "count": 5,
                "disable_get_url": True,
                "parse_mult_msg": True,
                "quick_reply": True,
                "reverse_order": True,
                "reverseOrder": True,
                "message_seq": 0,
                "user_id": 123456,
            },
        )
    ]


@pytest.mark.asyncio
async def test_get_msg_history_repairs_user_id_misused_as_group_id(monkeypatch):
    warnings = []
    monkeypatch.setattr("main.logger.warning", warnings.append)
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_get_msg_history_tool(
        event,
        count=10,
        group_id=123456,
        message_type="group",
    )

    assert event.bot.api.calls == [
        (
            "get_group_msg_history",
            {
                "count": 10,
                "disable_get_url": True,
                "parse_mult_msg": True,
                "quick_reply": True,
                "reverse_order": True,
                "reverseOrder": True,
                "message_seq": 0,
                "group_id": 654321,
            },
        )
    ]
    assert warnings == [
        "NapCat 工具参数 group_id 等于当前消息发送者 user_id，疑似把用户号误填为群号，已回退为当前群号。"
    ]


@pytest.mark.asyncio
async def test_target_id_alias_is_normalized_before_calling_api():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin._call_napcat_api(
        event,
        "send_poke",
        {"target_id": 3209552419},
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_poke",
            {"user_id": 3209552419, "group_id": 654321},
        )
    ]


@pytest.mark.asyncio
async def test_no_parameter_tool_calls_expected_endpoint():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_get_login_info_tool(event)

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [("get_login_info", {})]


def test_information_actions_are_classified_for_return_results():
    plugin = NapCatFunctionToolsPlugin(context=None)

    assert plugin._is_information_action("get_login_info") is True
    assert plugin._is_information_action("_get_group_notice") is True
    assert plugin._is_information_action("fetch_custom_face") is True
    assert plugin._is_information_action("can_send_image") is True
    assert plugin._is_information_action("check_url_safely") is True
    assert plugin._is_information_action("send_group_msg") is False
    assert plugin._is_information_action("set_group_admin") is False


@pytest.mark.asyncio
async def test_information_tool_returns_message_to_llm_without_chat_send():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_get_login_info_tool(event)
    payload = json.loads(result)

    assert isinstance(result, str)
    assert payload == {"status": "ok", "data": {}}
    assert event.bot.api.calls == [("get_login_info", {})]


@pytest.mark.asyncio
async def test_onebot_alias_parameters_are_expanded():
    event = make_aiocqhttp_event()
    plugin = NapCatFunctionToolsPlugin(context=None)

    await plugin.napcat_set_group_anonymous_ban_tool(
        event,
        group_id=123456,
        flag="anonymous-flag",
        duration=60,
    )

    assert event.bot.api.calls == [
        (
            "set_group_anonymous_ban",
            {"group_id": 123456, "duration": 60, "flag": "anonymous-flag"},
        )
    ]


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

    assert event.bot.api.calls == [("send_msg", {"message": "hello", "user_id": 123456})]


@pytest.mark.asyncio
async def test_call_napcat_api_can_timeout_action_when_requested():
    event = make_aiocqhttp_event()
    event.bot.api = SlowApi(delay=1.1)
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin._call_napcat_api(
        event,
        "get_group_list",
        {},
        timeout_seconds=1,
    )
    payload = json.loads(result)

    assert payload["status"] == "api_timeout"
    assert payload["endpoint"] == "get_group_list"
    assert event.bot.api.calls == [("get_group_list", {})]


@pytest.mark.asyncio
async def test_call_napcat_api_returns_llm_friendly_message_on_action_failure():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    event.bot.api = FailingApi(RuntimeError("ERR_GROUP_IS_DELETED"))
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin._call_napcat_api(
        event,
        "set_group_ban",
        {"group_id": 654321, "user_id": 123456, "duration": 3600},
    )
    payload = json.loads(result)

    assert payload["status"] == "api_error"
    assert payload["endpoint"] == "set_group_ban"
    assert payload["message"] == "ERR_GROUP_IS_DELETED"
    assert payload["error_type"] == "RuntimeError"
    assert payload["payload"]["group_id"] == 654321


@pytest.mark.asyncio
async def test_call_napcat_api_wraps_empty_action_result_for_llm():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    event.bot.api = NullApi()
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_group_sign_tool(event)
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert payload["endpoint"] == "send_group_sign"
    assert payload["data"] is None
    assert "没有返回业务数据" in payload["message"]
    assert event.bot.api.calls == [("send_group_sign", {"group_id": 654321})]


def test_translate_en2zh_tool_is_disabled_for_current_napcat_version():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)

    assert not hasattr(NapCatFunctionToolsPlugin, "napcat_translate_en2zh_tool")
    assert "napcat_translate_en2zh" not in {record.tool_name for record in records}


def test_get_mini_app_ark_tool_is_disabled_for_old_napcat_versions():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)

    assert not hasattr(NapCatFunctionToolsPlugin, "napcat_get_mini_app_ark_tool")
    assert "napcat_get_mini_app_ark" not in {record.tool_name for record in records}


def test_tool_name_keeps_internal_dot_endpoint_distinct():
    assert make_tool_name("napcat", ".ocr_image") == "napcat_dot_ocr_image"
    assert make_tool_name("napcat", "ocr_image") == "napcat_ocr_image"


def make_function_tool(name: str, active: bool = True):
    return FunctionTool(
        name=name,
        description=f"{name} description",
        parameters={"type": "object", "properties": {}},
        handler=None,
        active=active,
    )


def test_build_tool_registry_data_extracts_tool_discovery_metadata():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    by_name = {record.tool_name: record for record in records}

    assert len(records) == 160
    assert by_name["napcat_send_msg"].endpoint == "send_msg"
    assert by_name["napcat_send_msg"].method_name == "napcat_send_msg_tool"
    assert "times" not in json.loads(
        by_name["napcat_send_like"].required_parameters_json
    )
    assert "群聊或私聊" in by_name["napcat_send_msg"].capability

    params = json.loads(by_name["napcat_send_msg"].parameters_json)
    param_names = {param["name"] for param in params}
    assert {"group_id", "message", "message_type", "auto_escape"}.issubset(param_names)
    group_id_param = next(param for param in params if param["name"] == "group_id")
    assert "默认使用当前群聊" in group_id_param["description"]
    assert json.loads(by_name["napcat_send_msg"].required_parameters_json) == [
        "message",
        "message_type",
    ]
    assert json.loads(by_name["napcat_dot_ocr_image"].platforms_json) == ["windows"]
    assert json.loads(by_name["napcat_get_login_info"].platforms_json) == []


def test_tool_capability_prompts_are_concise_for_llm_discovery():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)

    for record in records:
        assert not record.capability.startswith("能力:")
        assert "API:" not in record.capability
        assert "|" not in record.capability


def test_todo_tracks_all_tools_and_prompt_progress():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    todo_text = (Path(__file__).resolve().parents[1] / "TODO.md").read_text(
        encoding="utf-8"
    )

    assert todo_text.count("- [") >= len(records)
    assert "- [x] 001. `napcat_bot_exit`" in todo_text
    assert todo_text.count("- [ ]") == 0


def test_tool_discovery_report_and_constraint_are_maintained():
    plugin_dir = Path(__file__).resolve().parents[1]
    report_text = (plugin_dir / "report" / "tool_discovery_report.md").read_text(
        encoding="utf-8"
    )
    constraints_text = (plugin_dir / "CONSTRAINTS.md").read_text(encoding="utf-8")
    readme_text = (plugin_dir / "README.md").read_text(encoding="utf-8")

    assert "工具发现逻辑报告书" in report_text
    assert "napcat_search_tools" in report_text
    assert "ToolRegistryRepo.search_tools" in report_text
    assert "risk_level 当前只进入结果元数据，不参与搜索排序" in report_text
    assert "report/tool_discovery_report.md" in constraints_text
    assert "一旦改动工具发现相关模块或行为" in constraints_text
    assert "python scripts/package_plugin.py" in constraints_text
    assert "report/tool_discovery_report.md" in readme_text
    assert "python scripts/package_plugin.py" in readme_text


def test_package_script_builds_astrbot_install_zip_from_tracked_files(tmp_path):
    plugin_dir = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "plugin.zip"

    result = subprocess.run(
        [
            sys.executable,
            str(plugin_dir / "scripts" / "package_plugin.py"),
            "--output",
            str(output_path),
        ],
        cwd=plugin_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    with zipfile.ZipFile(output_path) as zf:
        name_list = zf.namelist()
        names = set(name_list)

    package_root = "astrbot_plugin_napcat_fc/"
    assert name_list[0] == package_root
    assert f"{package_root}metadata.yaml" in names
    assert f"{package_root}main.py" in names
    assert f"{package_root}README.md" in names
    assert f"{package_root}napcat_fc/db/database.py" in names
    assert f"{package_root}TODO.md" not in names
    assert f"{package_root}CONSTRAINTS.md" not in names
    assert f"{package_root}待删除.md" not in names
    assert all(not name.startswith(f"{package_root}report/") for name in names)
    assert all(not name.startswith(f"{package_root}dist/") for name in names)


def test_package_script_reads_metadata_with_optional_utf8_bom():
    plugin_dir = Path(__file__).resolve().parents[1]
    script_path = plugin_dir / "scripts" / "package_plugin.py"
    spec = importlib.util.spec_from_file_location("package_plugin_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    name, version = module.read_metadata_name_and_version()
    assert name == "astrbot_plugin_napcat_fc"
    assert version.startswith("v")


def test_hot_update_reloads_internal_napcat_modules(monkeypatch):
    plugin_dir = Path(__file__).resolve().parents[1]
    reloaded = []

    for module_name in napcat_plugin_main.INTERNAL_MODULE_RELOAD_ORDER:
        fake_module = ModuleType(module_name)
        fake_module.__file__ = str(
            plugin_dir / Path(*module_name.split(".")).with_suffix(".py")
        )
        monkeypatch.setitem(sys.modules, module_name, fake_module)

    external_module = ModuleType("napcat_fc.external")
    external_module.__file__ = str(Path(sys.executable).resolve())
    monkeypatch.setitem(sys.modules, "napcat_fc.external", external_module)

    def fake_reload(module):
        reloaded.append(module.__name__)
        return module

    monkeypatch.setattr(napcat_plugin_main.importlib, "reload", fake_reload)

    napcat_plugin_main._reload_internal_modules_for_hot_update()

    assert reloaded == list(napcat_plugin_main.INTERNAL_MODULE_RELOAD_ORDER)
    assert "napcat_fc.external" not in reloaded


def test_optimized_tool_prompts_include_searchable_context():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    by_name = {record.tool_name: record for record in records}

    assert "发送语音" in by_name["napcat_can_send_record"].capability
    assert "群待办" in by_name["napcat_cancel_group_todo"].capability
    assert "内联键盘" in by_name["napcat_click_inline_keyboard_button"].capability
    assert "关键词提取" in by_name["napcat_dot_get_word_slices"].capability
    assert "OCR" in by_name["napcat_dot_ocr_image"].capability
    assert "二进制流" in by_name["napcat_download_file_image_stream"].capability
    assert "自定义表情" in by_name["napcat_fetch_custom_face"].capability
    assert "AI 声线" in by_name["napcat_get_ai_characters"].capability
    assert "鉴权信息" in by_name["napcat_get_credentials"].capability
    assert "群相册图片" in by_name["napcat_get_group_album_media_list"].capability
    assert "群文件容量" in by_name["napcat_get_group_file_system_info"].capability
    assert "频道服务器" in by_name["napcat_get_guild_list"].capability
    assert "频道成员详细资料" in by_name["napcat_get_guild_member_profile"].capability
    assert "图片 URL" in by_name["napcat_get_image"].capability
    assert "在线客户端" in by_name["napcat_get_online_clients"].capability
    assert "最近联系人" in by_name["napcat_get_recent_contact"].capability
    assert "健康检查" in by_name["napcat_get_status"].capability
    assert "OCR" in by_name["napcat_ocr_image"].capability
    assert "接收在线文件" in by_name["napcat_receive_online_file"].capability
    assert "群公告" in by_name["napcat_send_group_notice"].capability
    assert "频道通知" in by_name["napcat_send_guild_channel_msg"].capability
    assert "资料卡点赞" in by_name["napcat_send_like"].capability
    assert "群聊或私聊" in by_name["napcat_send_msg"].capability
    assert "message_id 自动组成 node 节点" in by_name["napcat_send_forward_msg"].capability
    forward_params = {
        param["name"]: param["description"]
        for param in json.loads(by_name["napcat_send_forward_msg"].parameters_json)
    }
    assert '{"type":"node","data":{"id": message_id}}' in forward_params["messages"]
    assert "单条要转发的消息 ID" in forward_params["message_id"]
    assert "多条要打包转发的消息 ID" in forward_params["message_ids"]
    assert "在线文件任务" in by_name["napcat_send_online_file"].capability
    assert "群精华消息" in by_name["napcat_set_essence_msg"].capability
    assert "好友申请" in by_name["napcat_set_friend_add_request"].capability
    assert "群管理员" in by_name["napcat_set_group_admin"].capability
    assert "踢出群成员" in by_name["napcat_set_group_kick"].capability
    assert "QQ 在线状态" in by_name["napcat_set_online_status"].capability
    assert "QQ 头像" in by_name["napcat_set_qq_avatar"].capability
    assert "群共享文件系统" in by_name["napcat_upload_group_file"].capability


def test_pending_delete_document_tracks_low_value_tool_candidates():
    pending_delete = Path(__file__).resolve().parents[1] / "待删除.md"
    text = pending_delete.read_text(encoding="utf-8")

    assert "已处理：优先删除" in text
    assert "建议默认禁用或隐藏" in text
    assert "已处理：合并" in text
    assert "不建议删除但应限制发现" in text
    assert "`napcat_unknown`" in text
    assert "`napcat_send_packet`" in text
    assert "`napcat_get_credentials`" in text
    assert "`napcat_get_credentials`" in text
    assert "`napcat_set_group_kick_members`" in text


def test_deleted_and_merged_tools_are_not_registered():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    tool_names = {record.tool_name for record in records}

    removed_tool_names = {
        "napcat_unknown",
        "napcat_send_packet",
        "napcat_test_download_stream",
        "napcat_nc_get_packet_status",
        "napcat_nc_get_rkey",
        "napcat_get_robot_uin_range",
        "napcat_reload_event_filter",
        "napcat_friend_poke",
        "napcat_group_poke",
        "napcat_forward_friend_single_msg",
        "napcat_forward_group_single_msg",
        "napcat_forward_single_msg",
        "napcat_get_friend_msg_history",
        "napcat_get_group_msg_history",
        "napcat_send_private_msg",
        "napcat_send_group_msg",
        "napcat_send_private_forward_msg",
        "napcat_send_group_forward_msg",
        "napcat_mark_group_msg_as_read",
        "napcat_mark_private_msg_as_read",
        "napcat_arksharegroup",
        "napcat_arksharepeer",
    }

    assert removed_tool_names.isdisjoint(tool_names)
    assert {
        "napcat_get_msg_history",
        "napcat_send_poke",
        "napcat_send_msg",
        "napcat_send_forward_msg",
        "napcat_mark_msg_as_read",
        "napcat_send_ark_share",
        "napcat_send_group_ark_share",
    }.issubset(tool_names)


def test_ark_share_tools_describe_auto_send_targets():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    by_name = {record.tool_name: record for record in records}

    ark_tool_names = {
        "napcat_send_group_ark_share",
        "napcat_send_ark_share",
    }
    for tool_name in ark_tool_names:
        assert by_name[tool_name].endpoint
        params = json.loads(by_name[tool_name].parameters_json)
        param_names = {param["name"] for param in params}
        assert {"send_group_id", "send_user_id"}.issubset(param_names)
        send_group_param = next(param for param in params if param["name"] == "send_group_id")
        send_user_param = next(param for param in params if param["name"] == "send_user_id")
        assert "默认发送到当前会话" in send_group_param["description"]
        assert "默认发送到当前会话" in send_user_param["description"]
        assert "发送" in by_name[tool_name].capability


@pytest.mark.asyncio
async def test_ark_share_tools_auto_send_to_current_group_when_target_omitted():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    event.bot.api = ArkApi()
    plugin = NapCatFunctionToolsPlugin(context=None)
    ark_json = '{"app":"com.tencent.contact.lua"}'

    result = await plugin.napcat_send_group_ark_share_tool(event)
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        ("send_group_ark_share", {"group_id": 654321}),
        (
            "send_group_msg",
            {
                "group_id": 654321,
                "message": [{"type": "json", "data": {"data": ark_json}}],
                },
        ),
    ]


@pytest.mark.asyncio
async def test_ark_share_tools_auto_send_direct_ark_json_string():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    ark_json = '{"app":"com.tencent.contact.lua","prompt":"group card"}'
    event.bot.api = ArkApi(ark_data=ark_json, direct_ark=True)
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_group_ark_share_tool(
        event,
        group_id=651906887,
        send_user_id=3527679745,
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        ("send_group_ark_share", {"group_id": 651906887}),
        (
            "send_private_msg",
            {
                    "message": [{"type": "json", "data": {"data": ark_json}}],
                    "user_id": 3527679745,
            },
        ),
    ]


@pytest.mark.asyncio
async def test_group_ark_share_zero_group_id_uses_current_group_before_auto_send():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    ark_json = '{"app":"com.tencent.contact.lua","prompt":"group card"}'
    event.bot.api = ArkApi(ark_data=ark_json)
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_group_ark_share_tool(
        event,
        group_id=0,
        send_user_id=3527679745,
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        ("send_group_ark_share", {"group_id": 654321}),
        (
            "send_private_msg",
            {
                    "message": [{"type": "json", "data": {"data": ark_json}}],
                    "user_id": 3527679745,
            },
        ),
    ]


@pytest.mark.asyncio
async def test_ark_share_invalid_send_target_falls_back_to_current_context(monkeypatch):
    warnings = []
    monkeypatch.setattr("main.logger.warning", warnings.append)
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    ark_json = '{"app":"com.tencent.contact.lua","prompt":"group card"}'
    event.bot.api = ArkApi(ark_data=ark_json)
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_send_group_ark_share_tool(
        event,
        group_id=654321,
        send_user_id="12345",
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        ("send_group_ark_share", {"group_id": 654321}),
        (
            "send_group_msg",
            {
                "group_id": 654321,
                "message": [{"type": "json", "data": {"data": ark_json}}],
            },
        ),
    ]
    assert warnings == [
        "NapCat 工具参数 send_user_id='12345' 小于 6 位或不是纯数字，已回退为当前会话默认值。"
    ]


@pytest.mark.asyncio
async def test_ark_share_tools_auto_send_to_explicit_private_target():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    event.bot.api = ArkApi()
    plugin = NapCatFunctionToolsPlugin(context=None)
    ark_json = '{"app":"com.tencent.contact.lua"}'

    result = await plugin.napcat_send_ark_share_tool(
        event,
        phone_number="13800138000",
        send_user_id=3527679745,
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        (
            "send_ark_share",
            {
                "phone_number": "13800138000",
                "group_id": 654321,
                "user_id": 123456,
            },
        ),
        (
            "send_private_msg",
            {
                    "message": [{"type": "json", "data": {"data": ark_json}}],
                    "user_id": 3527679745,
            },
        ),
    ]


@pytest.mark.asyncio
async def test_tool_registry_repo_roundtrip():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)[:3]
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tool-registry-{uuid.uuid4().hex}.db"
    )
    db = ToolDBManager(str(db_path))
    repo = ToolRegistryRepo(db)

    await db.init_db()
    try:
        assert await repo.replace_all_tools(records) == 3
        all_tools = await repo.list_tools()
        assert [record.tool_name for record in all_tools] == sorted(
            record.tool_name for record in records
        )

        target_name = records[0].tool_name
        target = await repo.get_tool(target_name)
        assert target is not None
        assert target.endpoint == records[0].endpoint

        assert await repo.set_tool_enabled(target_name, False) is True
        enabled_tools = await repo.list_tools(enabled_only=True)
        assert target_name not in {record.tool_name for record in enabled_tools}
        assert await repo.set_tool_enabled("missing_tool", False) is False

        assert await repo.sync_tools(records) == 3
        target = await repo.get_tool(target_name)
        assert target is not None
        assert target.enabled is False

        assert await repo.add_discovered_tool_names(
            ["tool_a", "tool_b", "tool_a", "tool_c"],
            max_size=3,
        ) == ["tool_b", "tool_a", "tool_c"]
        assert await repo.add_discovered_tool_names(["tool_d"], max_size=3) == [
            "tool_a",
            "tool_c",
            "tool_d",
        ]
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_tool_registry_persists_search_metadata_fields():
    records = [
        record
        for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
        if record.tool_name
        in {
            "napcat_send_msg",
            "napcat_set_group_ban",
            "napcat_get_version_info",
        }
    ]
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tool-registry-metadata-{uuid.uuid4().hex}.db"
    )
    db = ToolDBManager(str(db_path))
    repo = ToolRegistryRepo(db)

    await db.init_db()
    try:
        assert await repo.replace_all_tools(records) == 3

        send_msg = await repo.get_tool("napcat_send_msg")
        assert send_msg is not None
        assert send_msg.namespace == "message"
        assert "群聊消息" in json.loads(send_msg.aliases_json)
        assert send_msg.risk_level == "medium"
        assert send_msg.requires_confirmation is False
        assert send_msg.default_discoverable is True

        group_ban = await repo.get_tool("napcat_set_group_ban")
        assert group_ban is not None
        assert group_ban.namespace == "group_member"
        assert "禁言" in json.loads(group_ban.aliases_json)
        assert group_ban.risk_level == "high"
        assert group_ban.requires_confirmation is True

        version = await repo.get_tool("napcat_get_version_info")
        assert version is not None
        assert version.namespace == "system"
        assert version.risk_level == "low"
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_uses_namespace_and_aliases():
    records = [
        record
        for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
        if record.tool_name
        in {
            "napcat_set_group_ban",
            "napcat_get_group_shut_list",
            "napcat_get_version_info",
        }
    ]
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tool-registry-search-metadata-{uuid.uuid4().hex}.db"
    )
    db = ToolDBManager(str(db_path))
    repo = ToolRegistryRepo(db)

    await db.init_db()
    try:
        assert await repo.replace_all_tools(records) == 3

        alias_results = await repo.search_tools("禁言", limit=5)
        alias_names = [record.tool_name for record in alias_results]
        assert "napcat_set_group_ban" in alias_names
        assert "napcat_get_group_shut_list" in alias_names

        namespace_results = await repo.search_tools("system", limit=1)
        assert [record.tool_name for record in namespace_results] == [
            "napcat_get_version_info"
        ]

        assert repo.search_score(alias_results[0], "禁言") > 0
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_tool_db_init_migrates_old_tool_table_metadata_columns():
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tool-registry-migration-{uuid.uuid4().hex}.db"
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE napcat_tool (
                tool_name VARCHAR NOT NULL PRIMARY KEY,
                endpoint VARCHAR NOT NULL,
                method_name VARCHAR NOT NULL,
                capability VARCHAR NOT NULL DEFAULT '',
                parameters_json VARCHAR NOT NULL DEFAULT '[]',
                required_parameters_json VARCHAR NOT NULL DEFAULT '[]',
                platforms_json VARCHAR NOT NULL DEFAULT '[]',
                enabled BOOLEAN NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE napcat_discovered_tool (
                tool_name VARCHAR NOT NULL PRIMARY KEY,
                position INTEGER NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = ToolDBManager(str(db_path))
    repo = ToolRegistryRepo(db)
    records = [
        record
        for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
        if record.tool_name == "napcat_get_version_info"
    ]
    try:
        await db.init_db()
        assert await repo.replace_all_tools(records) == 1
        migrated = await repo.get_tool("napcat_get_version_info")
        assert migrated is not None
        assert migrated.namespace == "system"
        assert json.loads(migrated.aliases_json)
        assert migrated.risk_level == "low"
        assert migrated.default_discoverable is True
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_tool_db_init_warns_when_migrating_old_tool_table(monkeypatch):
    warnings = []
    monkeypatch.setattr("napcat_fc.db.database.logger.warning", warnings.append)
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tool-registry-migration-warning-{uuid.uuid4().hex}.db"
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE napcat_tool (
                tool_name VARCHAR NOT NULL PRIMARY KEY,
                endpoint VARCHAR NOT NULL,
                method_name VARCHAR NOT NULL,
                capability VARCHAR NOT NULL DEFAULT '',
                parameters_json VARCHAR NOT NULL DEFAULT '[]',
                required_parameters_json VARCHAR NOT NULL DEFAULT '[]',
                platforms_json VARCHAR NOT NULL DEFAULT '[]',
                enabled BOOLEAN NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE napcat_discovered_tool (
                tool_name VARCHAR NOT NULL PRIMARY KEY,
                position INTEGER NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = ToolDBManager(str(db_path))
    try:
        await db.init_db()
        assert len(warnings) == 1
        assert "旧版 napcat_tool 表结构" in warnings[0]
        assert "namespace" in warnings[0]
        assert "aliases_json" in warnings[0]
        assert "自动执行兼容迁移" in warnings[0]

        warnings.clear()
        db._initialized = False
        await db.init_db()
        assert warnings == []
    finally:
        await db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


def test_remove_registered_napcat_tools_removes_global_tool_residue():
    napcat_tool = make_function_tool("napcat_send_msg")
    other_tool = make_function_tool("other_tool")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([napcat_tool, other_tool]))

    plugin._remove_registered_napcat_tools()

    assert plugin.context.get_llm_tool_manager().get_func("napcat_send_msg") is None
    assert other_tool.active is True


def test_remove_registered_napcat_tools_removes_duplicate_global_residue():
    first_napcat_tool = make_function_tool("napcat_send_msg")
    second_napcat_tool = make_function_tool("napcat_send_msg")
    other_tool = make_function_tool("other_tool")
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([first_napcat_tool, other_tool, second_napcat_tool])
    )

    plugin._remove_registered_napcat_tools()

    tool_manager = plugin.context.get_llm_tool_manager()
    assert tool_manager.get_func("napcat_send_msg") is None
    assert tool_manager.get_func("other_tool") is other_tool


def test_debug_log_is_gated_by_config(monkeypatch):
    captured = []
    monkeypatch.setattr("main.logger.debug", captured.append)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]), config={"debug": False})

    plugin._debug_log("test_node", value=1)
    assert captured == []

    plugin.config["debug"] = True
    plugin._debug_log("test_node", value=1)
    assert captured
    assert "test_node" in captured[0]
    assert '"elapsed_ms":' in captured[0]
    assert '"delta_ms":' in captured[0]
    assert '"value": 1' in captured[0]


def test_platform_specific_tools_only_available_on_matching_system():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    plugin.current_platform_name = "linux"
    assert plugin._is_tool_available_on_current_platform("napcat_dot_ocr_image") is False
    assert plugin._is_tool_available_on_current_platform("napcat_get_login_info") is True

    plugin.current_platform_name = "windows"
    assert plugin._is_tool_available_on_current_platform("napcat_dot_ocr_image") is True


def test_search_scoring_supports_legacy_repo_without_public_score_method():
    class LegacyRepo:
        def _search_score(self, record, keyword):
            return 20 if keyword in record.capability.lower() else 0

    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    plugin.tool_registry_repo = LegacyRepo()
    record = SimpleNamespace(
        tool_name="napcat_get_group_info",
        endpoint="get_group_info",
        capability="获取群信息",
        parameters_json="[]",
    )

    assert plugin._combined_search_score(record, "群 信息", ["群", "信息"]) > 0


def test_search_candidate_limit_uses_config_with_default_and_minimum():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    assert plugin._get_search_candidate_limit() == 10

    plugin.config["search_candidate_limit"] = 5
    assert plugin._get_search_candidate_limit() == 5

    plugin.config["search_candidate_limit"] = "2"
    assert plugin._get_search_candidate_limit() == 2

    plugin.config["search_candidate_limit"] = 0
    assert plugin._get_search_candidate_limit() == 1

    plugin.config["search_candidate_limit"] = "invalid"
    assert plugin._get_search_candidate_limit() == 10


def test_search_result_serialization_accepts_legacy_record_without_metadata():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    record = SimpleNamespace(
        tool_name="napcat_get_version_info",
        endpoint="get_version_info",
        capability="获取 NapCat 版本信息",
    )

    assert plugin._serialize_search_tool_record(record) == {
        "name": "napcat_get_version_info",
        "endpoint": "get_version_info",
        "capability": "获取 NapCat 版本信息",
        "namespace": "",
        "risk_level": "low",
        "requires_confirmation": False,
        "parameters": [],
        "required_parameters": [],
        "call_tool": "napcat_call_tool",
        "call_example": {
            "tool_name": "napcat_get_version_info",
            "arguments": {},
        },
        "usage": (
            "调用 napcat_call_tool，tool_name 填 'napcat_get_version_info'，"
            "arguments 按 parameters 填写；可从当前会话推断的 group_id、user_id、"
            "message_id 等上下文字段可以省略。"
        ),
    }


def test_discovered_tool_limit_uses_config_with_default_and_minimum():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    assert plugin._get_discovered_tool_limit() == 20

    plugin.config["discovered_tool_limit"] = 7
    assert plugin._get_discovered_tool_limit() == 7

    plugin.config["discovered_tool_limit"] = "3"
    assert plugin._get_discovered_tool_limit() == 3

    plugin.config["discovered_tool_limit"] = 0
    assert plugin._get_discovered_tool_limit() == 1

    plugin.config["discovered_tool_limit"] = "invalid"
    assert plugin._get_discovered_tool_limit() == 20


def test_search_result_limit_uses_argument_with_default_and_minimum():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    assert plugin._get_search_result_limit() == 3
    assert plugin._get_search_result_limit(6) == 6
    assert plugin._get_search_result_limit("4") == 4
    assert plugin._get_search_result_limit(0) == 1
    assert plugin._get_search_result_limit("invalid") == 3


def test_search_result_format_uses_config_with_default_and_fallback():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    assert plugin._get_search_result_format() == "pipe"

    plugin.config["search_result_format"] = "tsv"
    assert plugin._get_search_result_format() == "tsv"

    plugin.config["search_result_format"] = "JSON"
    assert plugin._get_search_result_format() == "json"

    plugin.config["search_result_format"] = "invalid"
    assert plugin._get_search_result_format() == "pipe"


@pytest.mark.asyncio
async def test_on_llm_request_injects_only_stable_search_and_call_tools():
    source_tool = make_function_tool("napcat_send_msg", active=False)
    stale_tool = make_function_tool("napcat_get_login_info", active=True)
    other_tool = make_function_tool("other_tool", active=True)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([source_tool]))

    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-dynamic-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet([stale_tool, other_tool])

        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        assert req.func_tool.get_tool("napcat_get_login_info") is None
        assert req.func_tool.get_tool("other_tool") is other_tool
        assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is not None
        assert req.func_tool.get_tool(plugin.CALL_TOOL_NAME) is not None
        assert req.func_tool.get_tool("napcat_send_msg") is None
        assert source_tool.active is False
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_on_llm_request_ignores_discovered_queue_for_stable_two_tool_mode():
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([]),
    )

    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-lazy-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        await plugin.tool_registry_repo.replace_discovered_tool_names(
            ["napcat_send_msg"]
        )

        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        assert req.func_tool.get_tool("napcat_send_msg") is None
        assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is not None
        call_tool = req.func_tool.get_tool(plugin.CALL_TOOL_NAME)
        assert call_tool is not None
        assert call_tool.parameters["required"] == ["tool_name"]
        assert "arguments" in call_tool.parameters["properties"]
        assert "arguments" not in call_tool.parameters["required"]
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


def test_dynamic_tool_schema_marks_required_parameters_only():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    tool = plugin._build_tool_from_registry_record("napcat_send_msg")

    assert tool is not None
    assert tool.parameters["required"] == ["message", "message_type"]
    assert "group_id" in tool.parameters["properties"]
    assert "group_id" not in tool.parameters["required"]


def test_search_tool_schema_marks_keyword_required_only():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    req = ProviderRequest()
    req.func_tool = ToolSet()

    tool = plugin._build_search_tool(req)

    assert tool.parameters["required"] == ["keyword"]
    assert "result_limit" in tool.parameters["properties"]
    assert "result_limit" not in tool.parameters["required"]


def test_call_tool_schema_marks_tool_name_required_only():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    req = ProviderRequest()
    req.func_tool = ToolSet()

    tool = plugin._build_call_tool(req)

    assert tool.parameters["required"] == ["tool_name"]
    assert "arguments" in tool.parameters["properties"]
    assert "arguments" not in tool.parameters["required"]


def test_napcat_llm_request_hook_runs_after_legacy_uploaded_instances():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(
        encoding="utf-8"
    )

    assert "@filter.on_llm_request(priority=-150)" in source


def test_album_media_list_schema_keeps_attach_info_optional():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    tool = plugin._build_tool_from_registry_record("napcat_get_group_album_media_list")

    assert tool is not None
    assert tool.parameters["required"] == ["album_id"]
    assert "attach_info" in tool.parameters["properties"]
    assert "attach_info" not in tool.parameters["required"]


@pytest.mark.asyncio
async def test_album_media_list_defaults_attach_info_to_empty_string():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_get_group_album_media_list_tool(
        event,
        album_id="album_1",
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "get_group_album_media_list",
            {"album_id": "album_1", "attach_info": "", "group_id": 654321},
        )
    ]


@pytest.mark.asyncio
async def test_album_media_like_payload_uses_documented_argument_order():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin.napcat_set_group_album_media_like_tool(
        event,
        album_id="album_1",
        lloc="media_lloc",
        id="like_key",
        set=True,
    )

    assert '"status": "ok"' in result
    action, payload = event.bot.api.calls[0]
    assert action == "set_group_album_media_like"
    assert list(payload.keys()) == ["group_id", "album_id", "lloc", "id", "set"]
    assert payload == {
        "group_id": 654321,
        "album_id": "album_1",
        "lloc": "media_lloc",
        "id": "like_key",
        "set": True,
    }


def test_no_optional_doc_parameter_is_required_by_signature():
    issues = []
    for record in build_tool_registry_data(NapCatFunctionToolsPlugin):
        method = getattr(NapCatFunctionToolsPlugin, record.method_name)
        signature = inspect.signature(method)
        for parameter in json.loads(record.parameters_json):
            name = parameter["name"]
            description = parameter.get("description", "")
            signature_parameter = signature.parameters[name]
            if (
                "可选" in description
                and signature_parameter.default is inspect.Signature.empty
            ):
                issues.append(f"{record.tool_name}.{name}")

    assert issues == []


@pytest.mark.asyncio
async def test_on_llm_request_skips_napcat_tools_for_non_aiocqhttp_events():
    source_tool = make_function_tool("napcat_send_msg", active=False)
    stale_tool = make_function_tool("napcat_get_login_info", active=True)
    other_tool = make_function_tool("other_tool", active=True)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([source_tool]))
    req = ProviderRequest()
    req.func_tool = ToolSet([stale_tool, other_tool])

    await plugin.inject_napcat_tools_on_llm_request(object(), req)

    assert req.func_tool.get_tool("napcat_get_login_info") is None
    assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is None
    assert req.func_tool.get_tool(plugin.CALL_TOOL_NAME) is None
    assert req.func_tool.get_tool("napcat_send_msg") is None
    assert req.func_tool.get_tool("other_tool") is other_tool


@pytest.mark.asyncio
async def test_llm_request_normalizes_qq_keyword_to_napcat_for_current_user_text():
    event = make_aiocqhttp_event(
        group_id="654321",
        message_str="用 QQ 群打卡接口",
    )
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([]),
        config={"dynamic_injection_enabled": False},
    )
    req = ProviderRequest(
        prompt="帮我找 qq 打卡工具",
        contexts=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "当前用户说 QQ 群打卡"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/a.png"},
                    },
                ],
            },
            {"role": "assistant", "content": "QQ 这个词不应在助手历史里改写"},
        ],
    )
    req.func_tool = ToolSet()

    await plugin.inject_napcat_tools_on_llm_request(event, req)

    assert event.message_str == "用 napcat 群打卡接口"
    assert event.message_obj.message_str == "用 napcat 群打卡接口"
    assert req.prompt == "帮我找 napcat 打卡工具"
    assert req.contexts[0]["content"][0]["text"] == "当前用户说 napcat 群打卡"
    assert req.contexts[1]["content"] == "QQ 这个词不应在助手历史里改写"
    assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is not None
    assert req.func_tool.get_tool(plugin.CALL_TOOL_NAME) is not None


@pytest.mark.asyncio
async def test_search_tool_returns_call_instructions_without_injecting_tools():
    send_group_tool = make_function_tool("napcat_send_msg", active=False)
    get_group_tool = make_function_tool("napcat_get_group_list", active=False)
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([send_group_tool, get_group_tool]),
        config={"discovered_tool_limit": 1, "search_result_format": "json"},
    )
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name in {"napcat_send_msg", "napcat_get_group_list"}
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        assert search_tool is not None
        assert "消息发送与撤回" in search_tool.description
        assert "群管理" in search_tool.description
        assert "当前可用工具列表中没有明确可以完成用户目标" in search_tool.description
        assert "必须先调用本工具进行工具发现" in search_tool.description
        assert "result_limit" in search_tool.description
        assert "多次用同一个关键词搜索" in search_tool.description
        result = await search_tool.handler(make_aiocqhttp_event(), keyword="群")
        payload = json.loads(result)

        assert payload["result_limit"] == 3
        assert payload["execution_tool"] == plugin.CALL_TOOL_NAME
        assert 1 <= len(payload["matched_tools"]) <= 3
        first_match = payload["matched_tools"][0]
        assert first_match["call_tool"] == plugin.CALL_TOOL_NAME
        assert first_match["call_example"]["tool_name"] == first_match["name"]
        assert "parameters" in first_match
        assert "required_parameters" in first_match
        assert payload["injected_count"] == 0
        assert req.func_tool.get_tool("napcat_send_msg") is None
        assert await plugin.tool_registry_repo.list_discovered_tool_names() == []
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_tool_defaults_to_complete_pipe_result():
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-pipe-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()

        result = await plugin._run_search_tool(
            make_aiocqhttp_event(),
            req,
            keyword="send msg",
            result_limit=1,
        )

        assert result.startswith("format=pipe\n")
        assert "execution_tool=napcat_call_tool" in result
        assert "tool|napcat_send_msg" in result
        assert "endpoint|send_msg" in result
        assert "required_parameters|message,message_type" in result
        assert "parameter|message|string|required|" in result
        assert "parameter|message_type|string|required|" in result
        assert "parameter|group_id|integer|optional|" in result
        assert "call_tool|napcat_call_tool" in result
        assert '"tool_name":"napcat_send_msg"' in result
        assert "usage|调用 napcat_call_tool" in result
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_tool_can_return_complete_tsv_result():
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([]),
        config={"search_result_format": "tsv"},
    )
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-tsv-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()

        result = await plugin._run_search_tool(
            make_aiocqhttp_event(),
            req,
            keyword="send msg",
            result_limit=1,
        )

        assert result.startswith("format=tsv\n")
        assert "tool\tnapcat_send_msg" in result
        assert "endpoint\tsend_msg" in result
        assert "required_parameters\tmessage,message_type" in result
        assert "parameter\tmessage\tstring\trequired\t" in result
        assert "parameter\tmessage_type\tstring\trequired\t" in result
        assert "call_tool\tnapcat_call_tool" in result
        assert '"tool_name":"napcat_send_msg"' in result
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_registered_search_tool_uses_remembered_request_context():
    send_group_tool = make_function_tool("napcat_send_msg", active=False)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([send_group_tool]))
    plugin.config["search_result_format"] = "json"
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-registered-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        event = make_aiocqhttp_event()
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(event, req)

        result = await plugin.napcat_search_tools_tool(event, keyword="send msg")
        payload = json.loads(result)

        assert payload["execution_tool"] == plugin.CALL_TOOL_NAME
        assert payload["injected_count"] == 0
        assert req.func_tool.get_tool("napcat_send_msg") is None
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_call_tool_invokes_existing_tool_with_context_defaults():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    result = await plugin.napcat_call_tool(
        event,
        tool_name="napcat_send_msg",
        arguments={"message_type": "group", "message": "hello"},
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        (
            "send_msg",
            {
                "message_type": "group",
                "message": "hello",
                "group_id": 654321,
                "user_id": 123456,
            },
        )
    ]


@pytest.mark.asyncio
async def test_call_tool_accepts_json_string_arguments():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    result = await plugin.napcat_call_tool(
        event,
        tool_name="napcat_get_group_info",
        arguments='{"group_id": 654321}',
    )
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert event.bot.api.calls == [
        ("get_group_info", {"group_id": 654321})
    ]


@pytest.mark.asyncio
async def test_call_tool_returns_friendly_error_for_unknown_tool():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    result = await plugin.napcat_call_tool(
        event,
        tool_name="napcat_missing_tool",
        arguments={},
    )
    payload = json.loads(result)

    assert payload["ok"] is False
    assert payload["status"] == "unknown_tool"


@pytest.mark.asyncio
async def test_call_tool_returns_friendly_error_for_missing_required_arguments():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    result = await plugin.napcat_call_tool(
        event,
        tool_name="napcat_send_msg",
        arguments={"message": "hello"},
    )
    payload = json.loads(result)

    assert payload["ok"] is False
    assert payload["status"] == "missing_required_arguments"
    assert payload["missing_parameters"] == ["message_type"]


@pytest.mark.asyncio
async def test_search_tool_normalizes_qq_keyword_to_napcat():
    send_group_tool = make_function_tool("napcat_send_msg", active=False)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([send_group_tool]))
    plugin.config["search_result_format"] = "json"
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-qq-normalize-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_send_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        event = make_aiocqhttp_event()
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(event, req)

        result = await plugin.napcat_search_tools_tool(event, keyword="qq send msg")
        payload = json.loads(result)

        assert payload["original_keyword"] == "qq send msg"
        assert payload["keyword"] == "napcat send msg"
        assert payload["search_terms"] == ["napcat", "send", "msg"]
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_registered_search_tool_returns_error_without_remembered_request_context():
    event = make_aiocqhttp_event(user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([]))

    result = await plugin.napcat_search_tools_tool(event, keyword="send msg")
    payload = json.loads(result)

    assert payload["ok"] is False
    assert "当前 LLM 请求上下文" in payload["message"]


@pytest.mark.asyncio
async def test_search_tool_splits_terms_and_keeps_results_callable_without_injection():
    tool_names = {
        "napcat_get_group_info",
        "napcat_get_group_info_ex",
        "napcat_get_group_list",
        "napcat_get_group_member_info",
        "napcat_send_msg",
    }
    tools = [make_function_tool(tool_name, active=False) for tool_name in tool_names]
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext(tools),
        config={"search_candidate_limit": 4, "search_result_format": "json"},
    )
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-split-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name in tool_names
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        result = await search_tool.handler(
            make_aiocqhttp_event(),
            keyword="group info",
            result_limit=2,
        )
        payload = json.loads(result)
        matched_names = [tool["name"] for tool in payload["matched_tools"]]

        assert payload["search_terms"] == ["group", "info"]
        assert payload["candidate_limit"] == 4
        assert payload["result_limit"] == 2
        assert 1 <= len(matched_names) <= 2
        assert all(
            tool["call_tool"] == plugin.CALL_TOOL_NAME
            for tool in payload["matched_tools"]
        )
        assert all(req.func_tool.get_tool(tool_name) is None for tool_name in matched_names)
        assert await plugin.tool_registry_repo.list_discovered_tool_names() == []
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_tool_never_mutates_request_scope_or_discovered_queue():
    tool_names = {
        "napcat_get_group_info",
        "napcat_get_group_info_ex",
        "napcat_get_group_list",
        "napcat_get_group_member_info",
        "napcat_send_msg",
    }
    tools = [make_function_tool(tool_name, active=False) for tool_name in tool_names]
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext(tools),
        config={
            "discovered_tool_limit": 1,
            "search_candidate_limit": 5,
            "unlimited_request_tool_injection": True,
            "search_result_format": "json",
        },
    )
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-unlimited-request-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name in tool_names
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        first = json.loads(
            await search_tool.handler(
                make_aiocqhttp_event(),
                keyword="group",
                result_limit=2,
            )
        )
        second = json.loads(
            await search_tool.handler(
                make_aiocqhttp_event(),
                keyword="group",
                result_limit=2,
            )
        )
        request_scope_names = {
            name for name in tool_names if req.func_tool.get_tool(name) is not None
        }
        persisted_names = await plugin.tool_registry_repo.list_discovered_tool_names()

        assert first["injected_count"] == 0
        assert second["injected_count"] == 0
        assert first["execution_tool"] == plugin.CALL_TOOL_NAME
        assert second["execution_tool"] == plugin.CALL_TOOL_NAME
        assert request_scope_names == set()
        assert persisted_names == []
        assert second["request_scope_tool_count"] == len(request_scope_names)
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_tool_filters_platform_specific_results_before_persisting():
    ocr_tool = make_function_tool("napcat_dot_ocr_image", active=False)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([ocr_tool]))
    plugin.config["search_result_format"] = "json"
    plugin.current_platform_name = "linux"
    db_path = (
        Path(__file__).resolve().parents[1]
        / f".test-platform-search-tools-{uuid.uuid4().hex}.db"
    )
    plugin.tool_db = ToolDBManager(str(db_path))
    plugin.tool_registry_repo = ToolRegistryRepo(plugin.tool_db)
    await plugin.tool_db.init_db()
    try:
        records = [
            record
            for record in build_tool_registry_data(NapCatFunctionToolsPlugin)
            if record.tool_name == "napcat_dot_ocr_image"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        assert search_tool is not None
        result = await search_tool.handler(make_aiocqhttp_event(), keyword="ocr")
        payload = json.loads(result)

        assert payload["matched_tools"] == []
        assert await plugin.tool_registry_repo.list_discovered_tool_names() == []
        assert req.func_tool.get_tool("napcat_dot_ocr_image") is None
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()
