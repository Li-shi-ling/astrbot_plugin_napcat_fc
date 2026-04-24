from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EndpointSpec:
    endpoint: str
    method: str
    title: str
    source: str


PATH_RE = re.compile(r"(?m)^  /([^:\r\n]+):\s*\r?\n\s{4}([a-zA-Z]+):")
HEADING_RE = re.compile(r"(?m)^#{2,4}\s+`([^`]+)`\s*(.*)$")


def discover_all_endpoint_specs(plugin_dir: Path) -> list[EndpointSpec]:
    specs_by_endpoint = {
        spec.endpoint: spec
        for spec in discover_endpoint_specs(plugin_dir / "docs" / "napcat-apifox")
    }

    for docs_dir in (
        plugin_dir / "docs" / "onebot-11" / "api",
        plugin_dir / "docs" / "go-cqhttp" / "api",
    ):
        for spec in discover_markdown_heading_specs(docs_dir):
            specs_by_endpoint.setdefault(spec.endpoint, spec)

    return sorted(specs_by_endpoint.values(), key=lambda spec: spec.endpoint.lower())


def discover_endpoint_specs(docs_dir: Path) -> list[EndpointSpec]:
    if not docs_dir.exists():
        return []

    specs_by_endpoint: dict[str, EndpointSpec] = {}
    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PATH_RE.finditer(text):
            endpoint = match.group(1).strip()
            if not endpoint or endpoint in specs_by_endpoint:
                continue
            specs_by_endpoint[endpoint] = EndpointSpec(
                endpoint=endpoint,
                method=match.group(2).upper(),
                title=_title_from_path(path),
                source=str(path),
            )
    return sorted(specs_by_endpoint.values(), key=lambda spec: spec.endpoint.lower())


def discover_markdown_heading_specs(docs_dir: Path) -> list[EndpointSpec]:
    if not docs_dir.exists():
        return []

    specs_by_endpoint: dict[str, EndpointSpec] = {}
    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in HEADING_RE.finditer(text):
            endpoint = match.group(1).strip()
            if not _looks_like_endpoint(endpoint) or endpoint in specs_by_endpoint:
                continue
            title = match.group(2).strip() or _title_from_path(path)
            specs_by_endpoint[endpoint] = EndpointSpec(
                endpoint=endpoint,
                method="POST",
                title=title,
                source=str(path),
            )
    return sorted(specs_by_endpoint.values(), key=lambda spec: spec.endpoint.lower())


def make_tool_name(prefix: str, endpoint: str) -> str:
    normalized = endpoint.strip().strip("/")
    if normalized.startswith("."):
        normalized = f"dot_{normalized[1:]}"
    normalized = re.sub(r"[^0-9A-Za-z_]+", "_", normalized).strip("_").lower()
    if not normalized:
        normalized = "root"
    safe_prefix = re.sub(r"[^0-9A-Za-z_]+", "_", prefix).strip("_").lower()
    return f"{safe_prefix or 'napcat'}_{normalized}"


def _title_from_path(path: Path) -> str:
    stem = path.stem
    if "__" in stem:
        stem = stem.split("__", 1)[0]
    return stem.replace("_", " ").strip() or path.stem


def _looks_like_endpoint(value: str) -> bool:
    return bool(re.fullmatch(r"\.?[A-Za-z_][0-9A-Za-z_]*", value))
