from __future__ import annotations

import inspect
import json
import re

from .db.repo import ToolRegistryData


CALL_RE = re.compile(
    r"_call_(?:napcat_api|ark_share_and_send)\(\s*event,\s*'([^']+)'",
    re.MULTILINE,
)


def build_tool_registry_data(plugin_cls: type) -> list[ToolRegistryData]:
    """Build persisted discovery records from metadata-only tool markers."""

    tool_names_by_method = _read_tool_names_by_method(plugin_cls)
    platform_names = _read_platform_tool_names(plugin_cls)
    records: list[ToolRegistryData] = []

    for method_name, tool_name in sorted(tool_names_by_method.items()):
        method = getattr(plugin_cls, method_name)
        signature = inspect.signature(method)
        doc = inspect.getdoc(method) or ""
        parameters = _read_parameters(signature, doc)
        required = [
            item["name"]
            for item in parameters
            if item.get("required") is True
        ]
        platforms = [
            platform
            for platform, names in platform_names.items()
            if tool_name in names
        ]
        endpoint = _read_endpoint(method)
        capability = _read_capability(doc)
        namespace = _infer_namespace(tool_name, endpoint, capability, parameters)
        aliases = _build_aliases(tool_name, endpoint, capability, namespace, parameters)
        risk_level = _infer_risk_level(tool_name, endpoint, capability)
        records.append(
            ToolRegistryData(
                tool_name=tool_name,
                endpoint=endpoint,
                method_name=method_name,
                capability=capability,
                namespace=namespace,
                aliases_json=json.dumps(
                    aliases, ensure_ascii=False, separators=(",", ":")
                ),
                risk_level=risk_level,
                requires_confirmation=risk_level == "high",
                default_discoverable=True,
                parameters_json=json.dumps(
                    parameters, ensure_ascii=False, separators=(",", ":")
                ),
                required_parameters_json=json.dumps(
                    required, ensure_ascii=False, separators=(",", ":")
                ),
                platforms_json=json.dumps(
                    platforms, ensure_ascii=False, separators=(",", ":")
                ),
            )
        )

    return records


def _read_tool_names_by_method(plugin_cls: type) -> dict[str, str]:
    source = inspect.getsource(plugin_cls)
    pattern = re.compile(
        r"# napcat_tool:\s*([a-zA-Z0-9_]+)\s+async def ([a-zA-Z0-9_]+)\(",
        re.MULTILINE,
    )
    tool_names_by_method = {
        match.group(2): match.group(1) for match in pattern.finditer(source)
    }
    if tool_names_by_method:
        return tool_names_by_method

    legacy_pattern = re.compile(
        r"@filter\.llm_tool\(name='([^']+)'\)\s+async def ([a-zA-Z0-9_]+)\(",
        re.MULTILINE,
    )
    return {
        match.group(2): match.group(1) for match in legacy_pattern.finditer(source)
    }


def _read_platform_tool_names(plugin_cls: type) -> dict[str, tuple[str, ...]]:
    return {
        "windows": tuple(getattr(plugin_cls, "WINDOWS_TOOL_NAMES", ())),
        "linux": tuple(getattr(plugin_cls, "LINUX_TOOL_NAMES", ())),
        "mac": tuple(getattr(plugin_cls, "MAC_TOOL_NAMES", ())),
    }


def _read_parameters(signature: inspect.Signature, doc: str) -> list[dict]:
    descriptions = _read_arg_descriptions(doc)
    parameters: list[dict] = []
    for name, parameter in signature.parameters.items():
        if name in {"self", "event"}:
            continue
        annotation = _format_annotation(parameter.annotation)
        parameters.append(
            {
                "name": name,
                "type": annotation,
                "required": parameter.default is inspect.Signature.empty,
                "description": descriptions.get(name, ""),
            }
        )
    return parameters


def _read_arg_descriptions(doc: str) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for line in doc.splitlines():
        match = re.match(r"\s{4}([a-zA-Z_][a-zA-Z0-9_]*)\(([^)]+)\):\s*(.*)", line)
        if match:
            descriptions[match.group(1)] = match.group(3).strip()
    return descriptions


def _format_annotation(annotation) -> str:
    if annotation is inspect.Signature.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    name = getattr(annotation, "__name__", None)
    if name:
        return name
    return str(annotation).replace("typing.", "")


def _read_endpoint(method) -> str:
    source = inspect.getsource(method)
    match = CALL_RE.search(source)
    if match:
        return match.group(1)
    return ""


def _read_capability(doc: str) -> str:
    first_line = next((line.strip() for line in doc.splitlines() if line.strip()), "")
    if first_line.startswith("能力:"):
        first_line = first_line.removeprefix("能力:").strip()
    if first_line.startswith("鑳藉姏:"):
        first_line = first_line.removeprefix("鑳藉姏:").strip()
    first_line = re.sub(r"\s*\(API:\s*[^)]+\)\.?\s*$", "", first_line)
    return first_line.strip().rstrip("。")


def _infer_namespace(
    tool_name: str,
    endpoint: str,
    capability: str,
    parameters: list[dict],
) -> str:
    text = _metadata_text(tool_name, endpoint, capability, parameters)
    endpoint_text = endpoint.lower()
    tool_text = tool_name.lower()
    if any(token in text for token in ("ark", "card", "share")):
        return "ark"
    if any(token in text for token in ("guild", "channel")):
        return "guild"
    if any(token in text for token in ("ocr", "image", "photo", "record", "voice", "media")):
        return "media"
    if any(
        token in endpoint_text or token in tool_text
        for token in ("msg", "message", "forward", "reply")
    ):
        return "message"
    if "group" in text and any(
        token in text for token in ("file", "folder", "upload", "download", "album")
    ):
        return "group_file"
    if "group" in text and any(
        token in text
        for token in (
            "member",
            "admin",
            "ban",
            "kick",
            "card",
            "title",
            "honor",
            "mute",
        )
    ):
        return "group_member"
    if "group" in text:
        return "group_meta"
    if any(token in text for token in ("friend", "like", "stranger")):
        return "friend"
    if any(
        token in text
        for token in (
            "msg",
            "message",
            "forward",
            "reply",
            "poke",
            "reaction",
            "emoji",
            "essence",
        )
    ):
        return "message"
    if any(
        token in text
        for token in (
            "login",
            "status",
            "version",
            "restart",
            "cache",
            "packet",
            "online",
            "device",
            "rkey",
        )
    ):
        return "system"
    return "misc"


def _build_aliases(
    tool_name: str,
    endpoint: str,
    capability: str,
    namespace: str,
    parameters: list[dict],
) -> list[str]:
    aliases = {
        namespace,
        namespace.replace("_", " "),
        endpoint.replace("_", " "),
        tool_name.replace("napcat_", "").replace("_", " "),
    }
    aliases.update(_NAMESPACE_ALIASES.get(namespace, ()))
    for token, token_aliases in _TOKEN_ALIASES.items():
        if token in endpoint or token in tool_name or token in capability:
            aliases.update(token_aliases)
    for parameter in parameters:
        name = parameter.get("name")
        if name:
            aliases.add(str(name).replace("_", " "))
    aliases.discard("")
    return sorted(aliases)


def _infer_risk_level(tool_name: str, endpoint: str, capability: str) -> str:
    text = f"{tool_name} {endpoint} {capability}".lower()
    high_tokens = (
        "delete",
        "del_",
        "kick",
        "ban",
        "leave",
        "restart",
        "clean_cache",
        "set_group_admin",
        "set_group_whole_ban",
        "set_group_anonymous_ban",
        "set_group_kick",
        "set_group_leave",
    )
    if any(token in text for token in high_tokens):
        return "high"
    medium_tokens = (
        "send",
        "set_",
        "upload",
        "forward",
        "mark",
        "poke",
        "like",
        "handle",
        "approve",
        "reject",
    )
    if any(token in text for token in medium_tokens):
        return "medium"
    return "low"


def _metadata_text(
    tool_name: str,
    endpoint: str,
    capability: str,
    parameters: list[dict],
) -> str:
    parameter_names = " ".join(
        str(parameter.get("name", "")) for parameter in parameters
    )
    return f"{tool_name} {endpoint} {capability} {parameter_names}".lower()


_NAMESPACE_ALIASES = {
    "message": ("消息", "发消息", "撤回", "转发", "聊天", "回复", "群聊消息", "私聊消息"),
    "group_member": ("群成员", "成员管理", "禁言", "踢人", "管理员", "群名片", "头衔"),
    "group_file": ("群文件", "上传文件", "下载文件", "文件夹", "群相册", "相册"),
    "group_meta": ("群信息", "群列表", "群公告", "群设置", "群资料"),
    "friend": ("好友", "好友请求", "陌生人", "点赞", "备注"),
    "media": ("图片", "语音", "OCR", "识图", "媒体", "文件资源"),
    "guild": ("频道", "子频道", "频道身份组"),
    "system": ("登录", "状态", "版本", "缓存", "在线设备", "系统"),
    "ark": ("卡片", "分享卡片", "小程序", "Ark"),
    "misc": ("其他", "扩展接口"),
}


_TOKEN_ALIASES = {
    "send": ("发送", "发出", "推送"),
    "msg": ("消息", "聊天记录"),
    "message": ("消息", "聊天记录"),
    "group": ("群", "群聊"),
    "private": ("私聊", "好友聊天"),
    "friend": ("好友",),
    "file": ("文件",),
    "upload": ("上传",),
    "download": ("下载",),
    "image": ("图片",),
    "ocr": ("文字识别", "识别图片文字"),
    "album": ("相册", "群相册"),
    "ban": ("禁言",),
    "kick": ("踢人", "移出群"),
    "admin": ("管理员",),
    "version": ("版本",),
    "status": ("状态",),
    "ark": ("卡片", "分享卡片"),
}
