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
    """Build persisted discovery records from explicit llm_tool methods."""

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
        records.append(
            ToolRegistryData(
                tool_name=tool_name,
                endpoint=_read_endpoint(method),
                method_name=method_name,
                capability=_read_capability(doc),
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
        r"@filter\.llm_tool\(name='([^']+)'\)\s+async def ([a-zA-Z0-9_]+)\(",
        re.MULTILINE,
    )
    return {match.group(2): match.group(1) for match in pattern.finditer(source)}


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
    first_line = re.sub(r"\s*\(API:\s*[^)]+\)\.?\s*$", "", first_line)
    return first_line.strip().rstrip("。.")
