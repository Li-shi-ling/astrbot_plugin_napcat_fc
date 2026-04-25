from __future__ import annotations

import json
import re
import subprocess
import sys
import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

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


class ArkApi:
    def __init__(self, ark_data='{"app":"com.tencent.contact.lua"}'):
        self.ark_data = ark_data
        self.calls = []

    async def call_action(self, action, **payload):
        self.calls.append((action, payload))
        if action in {"ArkShareGroup", "ArkSharePeer", "send_ark_share", "send_group_ark_share"}:
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
):
    message = AstrBotMessage()
    message.type = MessageType.GROUP_MESSAGE if group_id else MessageType.FRIEND_MESSAGE
    message.message = list(message_components or [])
    message.message_str = ""
    message.sender = MessageMember(user_id=user_id, nickname="tester")
    message.self_id = "10000"
    message.message_id = message_id
    message.group_id = group_id
    message.session_id = group_id or user_id
    message.raw_message = raw_message
    return AiocqhttpMessageEvent(
        message_str="",
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


def test_main_registers_explicit_llm_tool_decorators():
    plugin_dir = Path(__file__).resolve().parents[1]
    specs = discover_all_endpoint_specs(plugin_dir)
    source = (plugin_dir / "main.py").read_text(encoding="utf-8")

    assert source.count("@filter.llm_tool") >= len(specs)
    assert "napcat_call_api" not in source
    assert "@filter.llm_tool(name='napcat_send_group_msg')" in source
    assert "@filter.llm_tool(name='napcat_send_private_msg')" in source
    assert "@filter.llm_tool(name='napcat_set_group_anonymous_ban')" in source
    send_group_signature = source.split("async def napcat_send_group_msg_tool(", 1)[1].split("):", 1)[0]
    assert "payload" not in send_group_signature
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
    registered_names = tuple(re.findall(r"@filter\.llm_tool\(name='([^']+)'\)", source))

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

    result = await plugin.napcat_send_group_msg_tool(
        event, group_id=123, message="hello", auto_escape=False
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "send_group_msg",
            {
                "group_id": 123,
                "message": "hello",
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

    await plugin.napcat_send_group_msg_tool(event, message="hello")

    assert event.bot.api.calls == [
        (
            "send_group_msg",
            {"group_id": 654321, "message": "hello", "user_id": 123456},
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
            "send_forward_msg",
            {
                "message": "hello",
                "messages": [],
                "group_id": 654321,
                "user_id": 123456,
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
            "send_forward_msg",
            {"message": "hello", "messages": [], "user_id": 123456},
        )
    ]


@pytest.mark.asyncio
async def test_target_id_alias_is_normalized_before_calling_api():
    event = make_aiocqhttp_event(group_id="654321", user_id="123456")
    plugin = NapCatFunctionToolsPlugin(context=None)

    result = await plugin._call_napcat_api(
        event,
        "friend_poke",
        {"target_id": 3209552419},
    )

    assert '"status": "ok"' in result
    assert event.bot.api.calls == [
        (
            "friend_poke",
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
        group_id=123,
        flag="anonymous-flag",
        duration=60,
    )

    assert event.bot.api.calls == [
        (
            "set_group_anonymous_ban",
            {"group_id": 123, "duration": 60, "flag": "anonymous-flag"},
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

    assert len(records) == 180
    assert by_name["napcat_send_group_msg"].endpoint == "send_group_msg"
    assert by_name["napcat_send_group_msg"].method_name == "napcat_send_group_msg_tool"
    assert "发送群消息" in by_name["napcat_send_group_msg"].capability

    params = json.loads(by_name["napcat_send_group_msg"].parameters_json)
    param_names = {param["name"] for param in params}
    assert {"group_id", "message", "auto_escape"}.issubset(param_names)
    group_id_param = next(param for param in params if param["name"] == "group_id")
    assert "默认使用当前群聊" in group_id_param["description"]
    assert json.loads(by_name["napcat_send_group_msg"].required_parameters_json) == [
        "message"
    ]
    assert json.loads(by_name["napcat_dot_ocr_image"].platforms_json) == ["windows"]
    assert json.loads(by_name["napcat_get_login_info"].platforms_json) == []


def test_ark_share_tools_describe_auto_send_targets():
    records = build_tool_registry_data(NapCatFunctionToolsPlugin)
    by_name = {record.tool_name: record for record in records}

    ark_tool_names = {
        "napcat_send_group_ark_share",
        "napcat_send_ark_share",
        "napcat_arksharegroup",
        "napcat_arksharepeer",
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
        assert "自动发送" in by_name[tool_name].capability


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
                "user_id": 123456,
            },
        ),
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
                "group_id": 654321,
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


def test_deactivate_registered_napcat_tools_marks_global_tools_inactive():
    napcat_tool = make_function_tool("napcat_send_group_msg")
    other_tool = make_function_tool("other_tool")
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([napcat_tool, other_tool]))

    plugin._deactivate_registered_napcat_tools()

    assert napcat_tool.active is False
    assert other_tool.active is True


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


@pytest.mark.asyncio
async def test_on_llm_request_injects_discovered_tools_as_request_scope_copies():
    source_tool = make_function_tool("napcat_send_group_msg", active=False)
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
            if record.tool_name == "napcat_send_group_msg"
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        await plugin.tool_registry_repo.replace_discovered_tool_names(
            ["napcat_send_group_msg"]
        )
        req = ProviderRequest()
        req.func_tool = ToolSet([stale_tool, other_tool])

        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        assert req.func_tool.get_tool("napcat_get_login_info") is None
        assert req.func_tool.get_tool("other_tool") is other_tool
        assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is not None
        injected = req.func_tool.get_tool("napcat_send_group_msg")
        assert injected is not None
        assert injected is not source_tool
        assert injected.active is True
        assert source_tool.active is False
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_on_llm_request_skips_napcat_tools_for_non_aiocqhttp_events():
    source_tool = make_function_tool("napcat_send_group_msg", active=False)
    stale_tool = make_function_tool("napcat_get_login_info", active=True)
    other_tool = make_function_tool("other_tool", active=True)
    plugin = NapCatFunctionToolsPlugin(context=FakeContext([source_tool]))
    req = ProviderRequest()
    req.func_tool = ToolSet([stale_tool, other_tool])

    await plugin.inject_napcat_tools_on_llm_request(object(), req)

    assert req.func_tool.get_tool("napcat_get_login_info") is None
    assert req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME) is None
    assert req.func_tool.get_tool("napcat_send_group_msg") is None
    assert req.func_tool.get_tool("other_tool") is other_tool


@pytest.mark.asyncio
async def test_search_tool_discovers_persists_and_immediately_injects_tools():
    send_group_tool = make_function_tool("napcat_send_group_msg", active=False)
    get_group_tool = make_function_tool("napcat_get_group_list", active=False)
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext([send_group_tool, get_group_tool])
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
            if record.tool_name in {"napcat_send_group_msg", "napcat_get_group_list"}
        ]
        await plugin.tool_registry_repo.replace_all_tools(records)
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        assert search_tool is not None
        assert "消息发送与撤回" in search_tool.description
        assert "群管理" in search_tool.description
        result = await search_tool.handler(make_aiocqhttp_event(), keyword="群")
        payload = json.loads(result)

        assert 1 <= len(payload["matched_tools"]) <= 3
        assert payload["injected_count"] >= 1
        assert req.func_tool.get_tool("napcat_send_group_msg") is not None
        assert len(await plugin.tool_registry_repo.list_discovered_tool_names()) <= 20
    finally:
        await plugin.tool_db.close()
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(db_path) + suffix)
            if path.exists():
                path.unlink()


@pytest.mark.asyncio
async def test_search_tool_splits_terms_and_skips_already_discovered_candidates():
    tool_names = {
        "napcat_get_group_info",
        "napcat_get_group_info_ex",
        "napcat_get_group_list",
        "napcat_get_group_member_info",
        "napcat_send_group_msg",
    }
    tools = [make_function_tool(tool_name, active=False) for tool_name in tool_names]
    plugin = NapCatFunctionToolsPlugin(
        context=FakeContext(tools),
        config={"search_candidate_limit": 4},
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
        await plugin.tool_registry_repo.replace_discovered_tool_names(
            ["napcat_get_group_info"]
        )
        req = ProviderRequest()
        req.func_tool = ToolSet()
        await plugin.inject_napcat_tools_on_llm_request(make_aiocqhttp_event(), req)

        search_tool = req.func_tool.get_tool(plugin.SEARCH_TOOL_NAME)
        result = await search_tool.handler(make_aiocqhttp_event(), keyword="group info")
        payload = json.loads(result)
        matched_names = [tool["name"] for tool in payload["matched_tools"]]

        assert payload["search_terms"] == ["group", "info"]
        assert payload["candidate_limit"] == 4
        assert "napcat_get_group_info" in payload["skipped_discovered_tools"]
        assert "napcat_get_group_info" not in matched_names
        assert 1 <= len(matched_names) <= 3
        assert all(req.func_tool.get_tool(tool_name) is not None for tool_name in matched_names)
        assert (
            await plugin.tool_registry_repo.list_discovered_tool_names()
        )[-len(matched_names) :] == matched_names
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
