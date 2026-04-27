from __future__ import annotations

import asyncio
import importlib
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.core.agent.tool import ToolSet
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

PLUGIN_DIR = Path(__file__).resolve().parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

INTERNAL_MODULE_RELOAD_ORDER = (
    "napcat_fc.db.tables",
    "napcat_fc.db.database",
    "napcat_fc.db.repo",
    "napcat_fc.db",
    "napcat_fc.tool_registry",
)


def _reload_internal_modules_for_hot_update():
    for module_name in INTERNAL_MODULE_RELOAD_ORDER:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            module_path = Path(module_file).resolve()
            module_path.relative_to(PLUGIN_DIR)
        except (OSError, ValueError):
            continue
        importlib.reload(module)


_reload_internal_modules_for_hot_update()

from napcat_fc.db import ToolDBManager, ToolRegistryRepo
from napcat_fc.tool_registry import build_tool_registry_data


@register(
    "astrbot_plugin_napcat_fc",
    "Soulter / AstrBot contributors",
    "将 NapCat / OneBot / go-cqhttp API 注册为 AstrBot 函数工具。",
    "1.15.38",
)
class NapCatFunctionToolsPlugin(Star):
    SEARCH_TOOL_NAME = "napcat_search_tools"
    SEARCH_RESULT_LIMIT = 3
    SEARCH_CANDIDATE_LIMIT = 10
    DISCOVERED_TOOL_LIMIT = 20
    INFORMATION_ACTION_PREFIXES = (
        "get_",
        "_get_",
        "fetch_",
        "can_",
        "check_",
        "nc_get_",
        "qidian_get_",
    )
    WINDOWS_TOOL_NAMES = (
        'napcat_dot_ocr_image',
        'napcat_ocr_image',
    )
    LINUX_TOOL_NAMES = ()
    MAC_TOOL_NAMES = ()

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = dict(config or {})
        self.fallback_invalid_context_ids = bool(
            self.config.get("fallback_invalid_context_ids", True)
        )
        self.tool_count = 160
        self.tool_registry_records = build_tool_registry_data(type(self))
        self.tool_registry_records_by_name = {
            record.tool_name: record for record in self.tool_registry_records
        }
        self.action_parameter_names = self._build_action_parameter_names()
        self.napcat_tool_names = tuple(
            record.tool_name for record in self.tool_registry_records
        )
        self.platform_specific_tool_names = {
            "windows": set(self.WINDOWS_TOOL_NAMES),
            "linux": set(self.LINUX_TOOL_NAMES),
            "mac": set(self.MAC_TOOL_NAMES),
        }
        self.current_platform_name = self._detect_current_platform()
        self.storage_dir = str(StarTools.get_data_dir())
        os.makedirs(self.storage_dir, exist_ok=True)
        self.db_path = os.path.join(self.storage_dir, "napcat_fc_tools.db")
        self.tool_db = ToolDBManager(db_path=self.db_path)
        self.tool_registry_repo = ToolRegistryRepo(self.tool_db)
        self._debug_started_at = time.perf_counter()
        self._debug_last_at = self._debug_started_at
        self._provider_requests_by_event_id: dict[int, ProviderRequest] = {}

    def _build_action_parameter_names(self) -> dict[str, set[str]]:
        action_parameter_names: dict[str, set[str]] = {}
        for record in self.tool_registry_records:
            try:
                params = json.loads(record.parameters_json)
            except json.JSONDecodeError:
                params = []
            action_parameter_names[record.endpoint] = {
                item["name"]
                for item in params
                if isinstance(item, dict) and item.get("name")
            }
        return action_parameter_names

    async def initialize(self):
        self._debug_log("initialize:start", tool_count=self.tool_count, db_path=self.db_path)
        await self.tool_db.init_db()
        self._debug_log("initialize:db_ready")
        await self.tool_registry_repo.sync_tools(self.tool_registry_records)
        self._debug_log(
            "initialize:tool_registry_synced",
            record_count=len(self.tool_registry_records),
        )
        self._remove_registered_napcat_tools()
        logger.info(
            f"NapCat 函数工具已初始化：{self.tool_count} 个，"
            f"工具管理数据库已同步：{len(self.tool_registry_records)} 个，"
            "具体工具按需注入。"
        )
        self._debug_log("initialize:done")

    async def terminate(self):
        self._debug_log("terminate:start")
        await self.tool_db.close()
        self._debug_log("terminate:db_closed")
        return None

    @filter.on_llm_request(priority=-100)
    async def inject_napcat_tools_on_llm_request(
        self, event: AstrMessageEvent, req: ProviderRequest
    ):
        """在 LLM 请求阶段按工具管理数据库动态注入 NapCat 工具。"""
        self._debug_log(
            "llm_request:start",
            event_type=type(event).__name__,
            is_aiocqhttp=self._is_aiocqhttp_event(event),
        )
        self._unload_request_scope_napcat_tools(req)
        if not self._is_aiocqhttp_event(event):
            self._debug_log("llm_request:skip_non_aiocqhttp")
            return

        self._normalize_current_user_request_keywords(event, req)
        self._remember_provider_request(event, req)
        self._ensure_request_tool_set(req)
        req.func_tool.add_tool(self._build_search_tool(req))
        self._debug_log("llm_request:search_tool_injected")
        if self.config.get("dynamic_injection_enabled", True) is False:
            self._debug_log("llm_request:dynamic_injection_disabled")
            return

        discovered_tool_names = await self.tool_registry_repo.list_discovered_tool_names()
        self._debug_log(
            "llm_request:discovered_queue_loaded",
            discovered_count=len(discovered_tool_names),
        )
        injected_count = self._inject_tool_names_into_request(req, discovered_tool_names)
        if injected_count:
            logger.debug(f"本轮 LLM 请求注入已发现 NapCat 工具：{injected_count} 个。")
        self._debug_log("llm_request:done", injected_count=injected_count)

    def _ensure_request_tool_set(self, req: ProviderRequest):
        if req.func_tool is None:
            req.func_tool = ToolSet()
            self._debug_log("request_tool_set:created")

    def _remember_provider_request(
        self, event: AstrMessageEvent, req: ProviderRequest
    ):
        self._provider_requests_by_event_id[id(event)] = req
        while len(self._provider_requests_by_event_id) > 64:
            oldest_key = next(iter(self._provider_requests_by_event_id))
            self._provider_requests_by_event_id.pop(oldest_key, None)
        self._debug_log(
            "request_context:remembered",
            tracked_count=len(self._provider_requests_by_event_id),
        )

    def _get_remembered_provider_request(
        self, event: AstrMessageEvent
    ) -> ProviderRequest | None:
        return self._provider_requests_by_event_id.get(id(event))

    def _replace_qq_keyword_with_napcat(self, text):
        if not isinstance(text, str) or "qq" not in text.lower():
            return text
        return re.sub(r"qq", "napcat", text, flags=re.IGNORECASE)

    def _normalize_current_user_request_keywords(
        self, event: AstrMessageEvent, req: ProviderRequest
    ):
        replacements = 0

        original_message = getattr(event, "message_str", None)
        normalized_message = self._replace_qq_keyword_with_napcat(original_message)
        if normalized_message != original_message:
            try:
                event.message_str = normalized_message
            except Exception:
                pass
            replacements += 1

        message_obj = getattr(event, "message_obj", None)
        original_obj_message = getattr(message_obj, "message_str", None)
        normalized_obj_message = self._replace_qq_keyword_with_napcat(
            original_obj_message
        )
        if normalized_obj_message != original_obj_message:
            try:
                message_obj.message_str = normalized_obj_message
            except Exception:
                pass
            replacements += 1

        original_prompt = getattr(req, "prompt", None)
        normalized_prompt = self._replace_qq_keyword_with_napcat(original_prompt)
        if normalized_prompt != original_prompt:
            req.prompt = normalized_prompt
            replacements += 1

        replacements += self._normalize_user_context_keywords(req)
        if replacements:
            self._debug_log(
                "request_keyword_normalized",
                rule="qq->napcat",
                replacements=replacements,
            )

    def _normalize_user_context_keywords(self, req: ProviderRequest) -> int:
        replacements = 0
        for ctx in getattr(req, "contexts", []) or []:
            if not isinstance(ctx, dict) or ctx.get("role") != "user":
                continue
            content = ctx.get("content")
            if isinstance(content, str):
                normalized = self._replace_qq_keyword_with_napcat(content)
                if normalized != content:
                    ctx["content"] = normalized
                    replacements += 1
                continue
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "text":
                    continue
                text = item.get("text")
                normalized = self._replace_qq_keyword_with_napcat(text)
                if normalized != text:
                    item["text"] = normalized
                    replacements += 1
        return replacements

    def _inject_tool_names_into_request(
        self, req: ProviderRequest, tool_names: list[str]
    ) -> int:
        self._debug_log("inject_tools:start", requested_count=len(tool_names))
        self._ensure_request_tool_set(req)
        injected_count = 0
        known_names = set(self.napcat_tool_names)
        for tool_name in dict.fromkeys(tool_names):
            if tool_name not in known_names:
                continue
            if not self._is_tool_available_on_current_platform(tool_name):
                self._debug_log(
                    "inject_tools:skip_platform_mismatch",
                    tool_name=tool_name,
                    current_platform=self.current_platform_name,
                )
                continue
            request_tool = self._build_tool_from_registry_record(tool_name)
            if request_tool is None:
                continue
            request_tool.active = True
            req.func_tool.add_tool(request_tool)
            injected_count += 1
            self._debug_log("inject_tools:tool_injected", tool_name=tool_name)
        self._debug_log("inject_tools:done", injected_count=injected_count)
        return injected_count

    def _get_request_scope_napcat_tool_names(
        self, req: ProviderRequest | None
    ) -> set[str]:
        if req is None or req.func_tool is None:
            return set()
        known_names = set(self.napcat_tool_names)
        return {
            tool.name
            for tool in req.func_tool.tools
            if getattr(tool, "name", None) in known_names
        }

    def _build_search_tool(self, req: ProviderRequest):
        async def search_handler(
            event: AstrMessageEvent,
            keyword: str,
            result_limit: int = None,
        ) -> str:
            """按关键词搜索 NapCat 工具，并立即注入本轮请求。"""
            return await self._run_search_tool(event, req, keyword, result_limit)

        tool = self.context.get_llm_tool_manager().spec_to_func(
            name=self.SEARCH_TOOL_NAME,
            func_args=[
                {
                    "name": "keyword",
                    "type": "string",
                    "description": (
                        "必填，搜索 NapCat 工具能力、工具名、API 名或参数名的关键词。"
                        "多个词用空格隔开时会并发分词搜索，并按综合相关度排序。"
                    ),
                },
                {
                    "name": "result_limit",
                    "type": "integer",
                    "description": (
                        "可选，本次最多加入持久化发现队列并注入当前请求的工具数量。"
                        "默认 3，最小有效值为 1。"
                    ),
                }
            ],
            desc=(
                "在 NapCat/OneBot/go-cqhttp 工具库中按关键词模糊搜索工具，"
                "支持空格分词并发查询，会先取综合相关度最高的一批候选，"
                "再排除已经发现过的工具，将剩余最相关的一批工具加入持久化发现队列，"
                "并立即注入本轮请求。"
                "可用 result_limit 控制本次加入工具列表的数量，默认 3。"
                "如果一次搜索没有覆盖足够多工具，可以多次用同一个关键词搜索；"
                "已发现工具会被跳过，后续搜索会继续补充更广泛的候选工具。"
                "可搜索的能力大类包括: 消息发送与撤回、群消息和私聊消息、"
                "合并转发和历史消息、群成员和群管理、好友和请求处理、"
                "群文件和文件下载、图片/语音/OCR、表情和收藏、账号状态、"
                "频道/频道身份组、资料查询、缓存清理和 NapCat 扩展接口。"
                "当当前可用工具列表中没有明确可以完成用户目标的 NapCat 工具时，"
                "必须先调用本工具进行工具发现；也可以在不知道具体 NapCat 工具名时调用。"
                "搜索后再使用返回并已注入的具体工具。"
            ),
            handler=search_handler,
        )
        self._apply_required_parameters(tool, ["keyword"])
        return tool

    @filter.llm_tool(name='napcat_search_tools')
    async def napcat_search_tools_tool(
        self,
        event: AstrMessageEvent,
        keyword: str,
        result_limit: int = None,
    ) -> str:
        """在 NapCat/OneBot/go-cqhttp 工具库中按关键词搜索工具，并注入当前 LLM 请求

Args:
    keyword(str): 必填，搜索 NapCat 工具能力、工具名、API 名或参数名的关键词；多个词用空格隔开时会并发分词搜索，并按综合相关度排序。
    result_limit(int): 可选，本次最多加入持久化发现队列并注入当前请求的工具数量；默认 3，最小有效值为 1。

Returns:
    str: 返回搜索结果、已注入工具、发现队列数量和跳过项的 JSON 字符串。"""
        req = self._get_remembered_provider_request(event)
        if req is None:
            return json.dumps(
                {
                    "ok": False,
                    "message": (
                        "napcat_search_tools 需要在当前 LLM 请求上下文中调用。"
                        "请先触发一次 aiocqhttp/NapCat 消息请求，再调用本工具。"
                    ),
                },
                ensure_ascii=False,
            )
        return await self._run_search_tool(event, req, keyword, result_limit)

    async def _run_search_tool(
        self,
        event: AstrMessageEvent,
        req: ProviderRequest,
        keyword: str,
        result_limit: int = None,
    ) -> str:
        if not self._is_aiocqhttp_event(event):
            self._debug_log(
                "search_tool:reject_non_aiocqhttp",
                event_type=type(event).__name__,
            )
            raise ValueError("NapCat search tool requires an aiocqhttp/NapCat message event.")

        original_keyword = keyword
        keyword = self._replace_qq_keyword_with_napcat(keyword)
        self._debug_log(
            "search_tool:start",
            keyword=keyword,
            original_keyword=original_keyword,
            event_type=type(event).__name__,
        )
        search_terms = self._build_search_terms(keyword)
        candidate_limit = self._get_search_candidate_limit()
        result_limit_value = self._get_search_result_limit(result_limit)
        candidate_records = await self._search_tool_candidates(
            keyword,
            search_terms,
            candidate_limit,
        )
        platform_records = [
            record
            for record in candidate_records
            if self._is_tool_available_on_current_platform(record.tool_name)
        ]
        discovered_names = set(
            await self.tool_registry_repo.list_discovered_tool_names()
        )
        request_scope_names = self._get_request_scope_napcat_tool_names(req)
        excluded_names = set(discovered_names)
        unlimited_request_injection = (
            self._is_unlimited_request_tool_injection_enabled()
        )
        if unlimited_request_injection:
            excluded_names.update(request_scope_names)
        skipped_discovered_names = [
            record.tool_name
            for record in platform_records
            if record.tool_name in excluded_names
        ]
        records = [
            record
            for record in platform_records
            if record.tool_name not in excluded_names
        ][:result_limit_value]
        matched_names = [record.tool_name for record in records]
        self._debug_log(
            "search_tool:matched",
            keyword=keyword,
            search_terms=search_terms,
            candidate_limit=candidate_limit,
            candidate_count=len(candidate_records),
            platform_candidate_count=len(platform_records),
            skipped_discovered_count=len(skipped_discovered_names),
            request_scope_tool_count=len(request_scope_names),
            unlimited_request_tool_injection=unlimited_request_injection,
            result_limit=result_limit_value,
            matched_count=len(matched_names),
            matched_tools=matched_names,
        )
        discovered_tool_limit = self._get_discovered_tool_limit()
        queue = await self.tool_registry_repo.add_discovered_tool_names(
            matched_names,
            max_size=discovered_tool_limit,
        )
        self._debug_log(
            "search_tool:queue_updated",
            queue_count=len(queue),
        )
        injected_count = 0
        if self.config.get("dynamic_injection_enabled", True) is not False:
            injected_count = self._inject_tool_names_into_request(req, matched_names)
        else:
            self._debug_log("search_tool:dynamic_injection_disabled")
        self._debug_log("search_tool:done", injected_count=injected_count)
        return json.dumps(
            {
                "keyword": keyword,
                "original_keyword": original_keyword,
                "search_terms": search_terms,
                "candidate_limit": candidate_limit,
                "result_limit": result_limit_value,
                "matched_tools": [
                    self._serialize_search_tool_record(record)
                    for record in records
                ],
                "injected_tools": matched_names,
                "injected_count": injected_count,
                "discovered_tool_count": len(queue),
                "max_discovered_tools": discovered_tool_limit,
                "request_scope_tool_count": len(
                    self._get_request_scope_napcat_tool_names(req)
                ),
                "unlimited_request_tool_injection": unlimited_request_injection,
                "skipped_discovered_tools": sorted(skipped_discovered_names),
            },
            ensure_ascii=False,
        )

    def _serialize_search_tool_record(self, record) -> dict:
        return {
            "name": record.tool_name,
            "endpoint": record.endpoint,
            "capability": record.capability,
            "namespace": getattr(record, "namespace", ""),
            "risk_level": getattr(record, "risk_level", "low"),
            "requires_confirmation": getattr(record, "requires_confirmation", False),
        }

    def _build_search_terms(self, keyword: str) -> list[str]:
        normalized = keyword.strip().lower()
        if not normalized:
            return []

        terms: list[str] = []
        for term in re.split(r"\s+", normalized):
            if not term:
                continue
            terms.append(term)
            if "_" in term:
                terms.extend(part for part in term.split("_") if len(part) >= 2)
        return list(dict.fromkeys(terms))

    def _get_search_candidate_limit(self) -> int:
        raw_limit = self.config.get("search_candidate_limit", self.SEARCH_CANDIDATE_LIMIT)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return self.SEARCH_CANDIDATE_LIMIT
        return max(1, limit)

    def _get_search_result_limit(self, result_limit=None) -> int:
        if result_limit is None:
            return self.SEARCH_RESULT_LIMIT
        try:
            limit = int(result_limit)
        except (TypeError, ValueError):
            return self.SEARCH_RESULT_LIMIT
        return max(1, limit)

    def _get_discovered_tool_limit(self) -> int:
        raw_limit = self.config.get("discovered_tool_limit", self.DISCOVERED_TOOL_LIMIT)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return self.DISCOVERED_TOOL_LIMIT
        return max(1, limit)

    def _is_unlimited_request_tool_injection_enabled(self) -> bool:
        return self.config.get("unlimited_request_tool_injection", False) is True

    def _build_tool_from_registry_record(self, tool_name: str):
        record = self.tool_registry_records_by_name.get(tool_name)
        if record is None:
            self._debug_log("tool_build:missing_record", tool_name=tool_name)
            return None
        handler = getattr(self, record.method_name, None)
        if handler is None:
            self._debug_log(
                "tool_build:missing_handler",
                tool_name=tool_name,
                method_name=record.method_name,
            )
            return None
        tool = self.context.get_llm_tool_manager().spec_to_func(
            name=record.tool_name,
            func_args=self._build_func_args_from_record(record),
            desc=record.capability,
            handler=handler,
        )
        self._apply_required_parameters(
            tool,
            self._load_required_parameter_names(record.required_parameters_json),
        )
        return tool

    def _apply_required_parameters(self, tool, required_parameter_names: list[str]):
        parameters = getattr(tool, "parameters", None)
        if not isinstance(parameters, dict):
            return
        properties = parameters.get("properties")
        if not isinstance(properties, dict):
            return
        required = [
            name
            for name in required_parameter_names
            if isinstance(name, str) and name in properties
        ]
        if required:
            parameters["required"] = required
        else:
            parameters.pop("required", None)

    def _load_required_parameter_names(self, required_parameters_json: str) -> list[str]:
        try:
            required = json.loads(required_parameters_json)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(required, list):
            return []
        return [name for name in required if isinstance(name, str)]

    def _build_func_args_from_record(self, record) -> list[dict]:
        try:
            parameters = json.loads(record.parameters_json)
        except (TypeError, json.JSONDecodeError):
            parameters = []
        func_args = []
        for parameter in parameters:
            if not isinstance(parameter, dict) or not parameter.get("name"):
                continue
            arg = {
                "name": parameter["name"],
                "type": self._normalize_json_schema_type(parameter.get("type")),
                "description": parameter.get("description", ""),
            }
            if arg["type"] == "array":
                arg["items"] = {"type": "object"}
            func_args.append(arg)
        return func_args

    def _normalize_json_schema_type(self, annotation: str | None) -> str:
        normalized = str(annotation or "string").strip().lower()
        normalized = normalized.replace("typing.", "")
        if normalized.startswith(("list", "tuple", "set")):
            return "array"
        if normalized.startswith(("dict", "mapping")):
            return "object"
        return {
            "str": "string",
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "any": "string",
            "none": "string",
        }.get(normalized, "string")

    async def _search_tool_candidates(
        self,
        keyword: str,
        terms: list[str],
        candidate_limit: int,
    ):
        if not terms:
            return []

        search_tasks = [
            self.tool_registry_repo.search_tools(
                term,
                limit=candidate_limit,
                enabled_only=True,
            )
            for term in terms
        ]
        search_results = await asyncio.gather(*search_tasks)
        by_name = {}
        for records in search_results:
            for record in records:
                by_name[record.tool_name] = record

        return sorted(
            by_name.values(),
            key=lambda record: (
                -self._combined_search_score(record, keyword, terms),
                record.tool_name,
            ),
        )[:candidate_limit]

    def _combined_search_score(self, record, keyword: str, terms: list[str]) -> int:
        full_keyword = keyword.strip().lower()
        score = 0
        if full_keyword:
            score += self._score_tool_record(record, full_keyword)
        matched_terms = 0
        for term in terms:
            term_score = self._score_tool_record(record, term)
            if term_score:
                matched_terms += 1
            score += term_score
        if matched_terms:
            score += matched_terms * 10
        if terms and matched_terms == len(terms):
            score += 40
        return score

    def _score_tool_record(self, record, keyword: str) -> int:
        normalized = keyword.strip().lower()
        if not normalized:
            return 0
        search_score = getattr(self.tool_registry_repo, "search_score", None)
        if callable(search_score):
            return search_score(record, normalized)
        legacy_search_score = getattr(self.tool_registry_repo, "_search_score", None)
        if callable(legacy_search_score):
            return legacy_search_score(record, normalized)

        score = 0
        tool_name = record.tool_name.lower()
        endpoint = record.endpoint.lower()
        capability = record.capability.lower()
        namespace = getattr(record, "namespace", "").lower()
        aliases = getattr(record, "aliases_json", "[]").lower()
        params = record.parameters_json.lower()
        if tool_name == normalized or endpoint == normalized:
            score += 100
        if namespace == normalized:
            score += 80
        if normalized in aliases:
            score += 45
        if tool_name.startswith(normalized) or endpoint.startswith(normalized):
            score += 50
        if normalized in tool_name:
            score += 30
        if normalized in endpoint:
            score += 25
        if normalized in namespace:
            score += 25
        if normalized in capability:
            score += 20
        if normalized in params:
            score += 5
        return score

    def _remove_registered_napcat_tools(self):
        if self.context is None:
            self._debug_log("global_tools_remove:skip_no_context")
            return
        tool_mgr = self.context.get_llm_tool_manager()
        remove_func = getattr(tool_mgr, "remove_func", None)
        if not callable(remove_func):
            self._debug_log("global_tools_remove:skip_no_remove_func")
            return
        removed_count = 0
        for tool_name in self.napcat_tool_names:
            while True:
                before_count = len(getattr(tool_mgr, "func_list", ()))
                remove_func(tool_name)
                after_count = len(getattr(tool_mgr, "func_list", ()))
                if after_count >= before_count:
                    break
                removed_count += before_count - after_count
        self._debug_log("global_tools_remove:done", removed_count=removed_count)

    def _unload_request_scope_napcat_tools(self, req: ProviderRequest | None):
        if req is None or req.func_tool is None:
            self._debug_log("request_tools_unload:skip_empty_request")
            return
        before_count = len(req.func_tool.tools)
        for tool_name in self.napcat_tool_names:
            req.func_tool.remove_tool(tool_name)
        removed_count = before_count - len(req.func_tool.tools)
        self._debug_log("request_tools_unload:done", removed_count=removed_count)

    def _debug_log(self, node: str, **fields):
        if self.config.get("debug", False) is not True:
            return
        now = time.perf_counter()
        elapsed_ms = round((now - self._debug_started_at) * 1000, 3)
        delta_ms = round((now - self._debug_last_at) * 1000, 3)
        self._debug_last_at = now
        fields = {
            "elapsed_ms": elapsed_ms,
            "delta_ms": delta_ms,
            **fields,
        }
        detail = ""
        if fields:
            detail = " " + json.dumps(fields, ensure_ascii=False, default=str)
        logger.debug(f"[NapCatFC] {node}{detail}")

    def _is_aiocqhttp_event(self, event: AstrMessageEvent) -> bool:
        return isinstance(event, AiocqhttpMessageEvent)

    def _is_tool_available_on_current_platform(self, tool_name: str) -> bool:
        for platform_name, tool_names in self.platform_specific_tool_names.items():
            if tool_name in tool_names:
                return platform_name == self.current_platform_name
        return True

    def _detect_current_platform(self) -> str:
        system = platform.system().strip().lower()
        if system.startswith("win"):
            return "windows"
        if system == "darwin":
            return "mac"
        if system.startswith("linux"):
            return "linux"
        return system or "unknown"

    async def _call_napcat_api(
        self,
        event: AstrMessageEvent,
        endpoint: str,
        payload: dict = None,
        timeout_seconds: float | None = None,
    ) -> str:
        if not isinstance(event, AiocqhttpMessageEvent):
            raise ValueError("NapCat tools require an aiocqhttp/NapCat message event.")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object.")
        action = endpoint.strip().lstrip("/")
        if not action:
            raise ValueError("endpoint must not be empty.")
        payload = dict(payload)
        self._normalize_contextual_target_params(event, action, payload)
        missing_action_default = await self._fill_action_specific_defaults(
            event,
            action,
            payload,
        )
        if missing_action_default:
            return json.dumps(
                {
                    "status": "missing_context",
                    "message": missing_action_default,
                    "endpoint": action,
                },
                ensure_ascii=False,
            )
        missing_context = self._fill_context_defaults(event, payload)
        if missing_context:
            return json.dumps(
                {
                    "status": "missing_context",
                    "message": missing_context,
                    "endpoint": action,
                },
                ensure_ascii=False,
            )
        bot = event.bot
        api = getattr(bot, "api", None)
        call_action = getattr(api, "call_action", None) or getattr(bot, "call_action", None)
        if not call_action:
            raise RuntimeError("Current aiocqhttp bot does not support call_action.")
        try:
            if timeout_seconds is None:
                result = await call_action(action, **payload)
            else:
                result = await asyncio.wait_for(
                    call_action(action, **payload),
                    timeout=float(timeout_seconds),
                )
        except TimeoutError:
            return json.dumps(
                {
                    "status": "api_timeout",
                    "retcode": 1408,
                    "data": None,
                    "message": (
                        f"NapCat API '{action}' did not respond within "
                        f"{float(timeout_seconds):g} seconds."
                    ),
                    "endpoint": action,
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {
                    "status": "api_error",
                    "retcode": getattr(exc, "retcode", None),
                    "data": None,
                    "message": str(exc),
                    "endpoint": action,
                    "payload": payload,
                    "error_type": type(exc).__name__,
                },
                ensure_ascii=False,
                default=str,
            )
        return self._format_napcat_return_message(action, result)

    def _is_information_action(self, action: str) -> bool:
        normalized_action = action.strip().lstrip("/")
        return normalized_action.startswith(self.INFORMATION_ACTION_PREFIXES)

    def _format_napcat_return_message(self, action: str, result) -> str:
        """LLM 工具通过 return 把 NapCat 结果交回模型，不直接发送聊天消息。"""
        if result is None:
            return json.dumps(
                {
                    "status": "ok",
                    "endpoint": action,
                    "data": None,
                    "message": (
                        f"NapCat API '{action}' 已完成调用，但接口没有返回业务数据。"
                    ),
                },
                ensure_ascii=False,
            )
        if self._is_information_action(action):
            return json.dumps(result, ensure_ascii=False, default=str)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def _call_ark_share_and_send(
        self,
        event: AstrMessageEvent,
        endpoint: str,
        payload: dict,
        send_group_id=None,
        send_user_id=None,
    ) -> str:
        ark_result_text = await self._call_napcat_api(event, endpoint, payload)
        try:
            ark_result = json.loads(ark_result_text)
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "status": "invalid_ark_response",
                    "endpoint": endpoint,
                    "ark_response": ark_result_text,
                    "message": "Ark 接口返回值不是 JSON，无法自动发送卡片。",
                },
                ensure_ascii=False,
            )

        ark_data = self._extract_ark_message_data(ark_result)
        if ark_data is None:
            return json.dumps(
                {
                    "status": "missing_ark_data",
                    "endpoint": endpoint,
                    "ark_response": ark_result,
                    "message": "Ark 接口返回 JSON 中没有 data 字段，无法自动发送卡片。",
                },
                ensure_ascii=False,
                default=str,
            )

        targets = self._resolve_ark_send_targets(event, send_group_id, send_user_id)
        if targets.get("status") == "missing_context":
            targets["endpoint"] = endpoint
            targets["ark_response"] = ark_result
            return json.dumps(targets, ensure_ascii=False, default=str)

        message = [{"type": "json", "data": {"data": ark_data}}]
        send_results = []
        for group_id in targets["group_ids"]:
            send_text = await self._call_napcat_api(
                event,
                "send_group_msg",
                {"group_id": group_id, "message": message},
            )
            send_results.append(
                {
                    "target_type": "group",
                    "target_id": group_id,
                    "result": self._loads_json_or_text(send_text),
                }
            )
        for user_id in targets["user_ids"]:
            send_text = await self._call_napcat_api(
                event,
                "send_private_msg",
                {"user_id": user_id, "message": message},
            )
            send_results.append(
                {
                    "target_type": "private",
                    "target_id": user_id,
                    "result": self._loads_json_or_text(send_text),
                }
            )

        return json.dumps(
            {
                "status": "ok",
                "endpoint": endpoint,
                "ark_response": ark_result,
                "send_results": send_results,
            },
            ensure_ascii=False,
            default=str,
        )

    def _extract_ark_message_data(self, ark_result):
        if isinstance(ark_result, dict):
            if ark_result.get("data") is not None:
                data = ark_result["data"]
                return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
            if self._looks_like_ark_payload(ark_result):
                return json.dumps(ark_result, ensure_ascii=False)
            return None
        if isinstance(ark_result, str):
            text = ark_result.strip()
            if not text:
                return None
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return text
            if isinstance(parsed, dict):
                if parsed.get("data") is not None:
                    data = parsed["data"]
                    return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
                if self._looks_like_ark_payload(parsed):
                    return text
            return text
        return None

    def _looks_like_ark_payload(self, payload: dict) -> bool:
        return any(key in payload for key in ("app", "meta", "view", "ver", "prompt"))

    def _resolve_ark_send_targets(
        self,
        event: AstrMessageEvent,
        send_group_id=None,
        send_user_id=None,
    ) -> dict:
        group_ids = []
        user_ids = []
        if (
            send_group_id is not None
            and not self._should_use_context_default_for_id(
                "send_group_id",
                send_group_id,
            )
        ):
            group_ids.append(self._normalize_numeric_id(send_group_id))
        if (
            send_user_id is not None
            and not self._should_use_context_default_for_id(
                "send_user_id",
                send_user_id,
            )
        ):
            user_ids.append(self._normalize_numeric_id(send_user_id))
        if group_ids or user_ids:
            return {"group_ids": group_ids, "user_ids": user_ids}

        if not isinstance(event, AiocqhttpMessageEvent):
            return {
                "status": "missing_context",
                "message": "当前消息不是 aiocqhttp/NapCat 事件，无法自动选择 Ark 卡片发送目标。",
            }

        group_id = event.get_group_id()
        if group_id:
            return {
                "group_ids": [self._normalize_numeric_id(group_id)],
                "user_ids": [],
            }
        user_id = event.get_sender_id()
        if user_id:
            return {
                "group_ids": [],
                "user_ids": [self._normalize_numeric_id(user_id)],
            }
        return {
            "status": "missing_context",
            "message": "当前会话无法自动获取群号或用户 ID，请提供 send_group_id 或 send_user_id。",
        }

    def _normalize_numeric_id(self, value):
        return int(value) if str(value).isdigit() else value

    def _is_context_default_marker(self, value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            value = value.strip()
            return value == "" or value == "0"
        return value == 0

    def _is_invalid_context_id(self, value) -> bool:
        if self._is_context_default_marker(value):
            return True
        text = str(value).strip()
        return not text.isdigit() or len(text) < 6

    def _should_use_context_default_for_id(self, field_name: str, value) -> bool:
        if self._is_context_default_marker(value):
            if value not in (None, ""):
                logger.warning(
                    f"NapCat 工具参数 {field_name}={value!r} 无效，已回退为当前会话默认值。"
                )
            return True
        if not self.fallback_invalid_context_ids:
            return False
        if not self._is_invalid_context_id(value):
            return False
        logger.warning(
            f"NapCat 工具参数 {field_name}={value!r} 小于 6 位或不是纯数字，已回退为当前会话默认值。"
        )
        return True

    def _loads_json_or_text(self, text: str):
        try:
            return json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return text

    async def _fill_action_specific_defaults(
        self,
        event: AiocqhttpMessageEvent,
        action: str,
        payload: dict,
    ) -> str | None:
        if action != "upload_image_to_qun_album":
            return None
        if payload.get("file"):
            return None
        image_file = await self._get_default_image_file(event)
        if not image_file:
            return "当前消息和被回复消息中都没有可用于上传群相册的图片。请发送或回复一张图片，或明确提供图片路径、URL、base64。"
        payload["file"] = image_file
        return None

    def _get_current_group_id_or_none(self, event: AstrMessageEvent):
        if not isinstance(event, AiocqhttpMessageEvent):
            return None
        group_id = event.get_group_id()
        if not group_id:
            return None
        return int(group_id) if str(group_id).isdigit() else group_id

    def _get_current_user_id_or_none(self, event: AstrMessageEvent):
        if not isinstance(event, AiocqhttpMessageEvent):
            return None
        user_id = event.get_sender_id()
        if not user_id:
            return None
        return int(user_id) if str(user_id).isdigit() else user_id

    def _normalize_contextual_target_params(
        self,
        event: AiocqhttpMessageEvent,
        action: str,
        payload: dict,
    ) -> None:
        parameter_names = self.action_parameter_names.get(action, set())
        has_user_id = "user_id" in parameter_names
        has_group_id = "group_id" in parameter_names
        has_message_id = "message_id" in parameter_names

        if has_user_id and payload.get("user_id") is None and "target_id" in payload:
            target_id = payload.pop("target_id")
            if target_id is not None:
                payload["user_id"] = target_id
        elif has_user_id and "target_id" in payload:
            payload.pop("target_id", None)

        if has_user_id and "user_id" not in payload:
            payload["user_id"] = None

        if has_group_id and "group_id" not in payload:
            group_id = self._get_current_group_id_or_none(event)
            if group_id is not None:
                payload["group_id"] = group_id

        if has_message_id and "message_id" not in payload:
            payload["message_id"] = None

    def _fill_context_defaults(
        self,
        event: AiocqhttpMessageEvent,
        payload: dict,
    ) -> str | None:
        if (
            "group_id" in payload
            and self._should_use_context_default_for_id(
                "group_id",
                payload.get("group_id"),
            )
        ):
            group_id = event.get_group_id()
            if not group_id:
                return "当前消息不是群聊事件，无法自动获取 group_id。请让用户提供群号，或改用私聊相关工具。"
            payload["group_id"] = int(group_id) if str(group_id).isdigit() else group_id

        current_group_id = self._get_current_group_id_or_none(event)
        current_user_id = self._get_current_user_id_or_none(event)
        if (
            self.fallback_invalid_context_ids
            and "group_id" in payload
            and current_group_id is not None
            and current_user_id is not None
            and self._normalize_numeric_id(payload.get("group_id")) == current_user_id
            and current_group_id != current_user_id
        ):
            logger.warning(
                "NapCat 工具参数 group_id 等于当前消息发送者 user_id，"
                "疑似把用户号误填为群号，已回退为当前群号。"
            )
            payload["group_id"] = current_group_id

        if (
            "user_id" in payload
            and self._should_use_context_default_for_id(
                "user_id",
                payload.get("user_id"),
            )
        ):
            user_id = event.get_sender_id()
            if not user_id:
                return "当前消息无法自动获取 user_id。请让用户提供 QQ 号或目标用户 ID。"
            payload["user_id"] = int(user_id) if str(user_id).isdigit() else user_id

        if (
            "self_id" in payload
            and self._should_use_context_default_for_id(
                "self_id",
                payload.get("self_id"),
            )
        ):
            self_id = event.get_self_id()
            if not self_id:
                return "当前消息无法自动获取 self_id。请明确提供机器人账号 ID。"
            payload["self_id"] = int(self_id) if str(self_id).isdigit() else self_id

        if (
            "message_id" in payload
            and self._is_context_default_marker(payload.get("message_id"))
        ):
            message_id = self._get_default_message_id(event)
            if not message_id:
                return "当前消息无法自动获取 message_id。请明确提供消息 ID。"
            payload["message_id"] = (
                int(message_id) if str(message_id).isdigit() else message_id
            )

        return None

    def _get_default_message_id(self, event: AiocqhttpMessageEvent):
        reply_message_id = self._get_replied_message_id(event)
        if self._has_value(reply_message_id):
            return reply_message_id
        return getattr(event.message_obj, "message_id", "")

    def _get_replied_message_id(self, event: AiocqhttpMessageEvent):
        message_obj = getattr(event, "message_obj", None)
        for component in getattr(message_obj, "message", []) or []:
            component_type = str(getattr(component, "type", "")).lower()
            if component_type.endswith("reply"):
                reply_id = getattr(component, "id", None)
                if self._has_value(reply_id):
                    return reply_id

        raw_message = getattr(message_obj, "raw_message", None)
        raw_segments = getattr(raw_message, "message", None)
        if not isinstance(raw_segments, list):
            return None
        for segment in raw_segments:
            if not isinstance(segment, dict) or segment.get("type") != "reply":
                continue
            data = segment.get("data") or {}
            if not isinstance(data, dict):
                continue
            reply_id = data.get("id") or data.get("message_id")
            if self._has_value(reply_id):
                return reply_id
        return None

    async def _get_default_image_file(self, event: AiocqhttpMessageEvent):
        message_obj = getattr(event, "message_obj", None)
        current_components = list(getattr(message_obj, "message", []) or [])

        for component in current_components:
            component_type = str(getattr(component, "type", "")).lower()
            if not component_type.endswith("reply"):
                continue
            image_file = await self._get_first_image_file_from_components(
                getattr(component, "chain", []) or []
            )
            if self._has_value(image_file):
                return image_file

        image_file = self._get_first_image_file_from_raw_reply(event)
        if self._has_value(image_file):
            return image_file

        image_file = await self._get_first_image_file_from_components(current_components)
        if self._has_value(image_file):
            return image_file

        return self._get_first_image_file_from_raw_segments(event)

    async def _get_first_image_file_from_components(self, components):
        for component in components or []:
            component_type = str(getattr(component, "type", "")).lower()
            if not component_type.endswith("image"):
                continue
            image_file = (
                getattr(component, "url", None)
                or getattr(component, "file", None)
                or getattr(component, "path", None)
            )
            if self._has_value(image_file):
                return image_file
            convert_to_base64 = getattr(component, "convert_to_base64", None)
            if convert_to_base64:
                return f"base64://{await convert_to_base64()}"
        return None

    def _get_first_image_file_from_raw_reply(self, event: AiocqhttpMessageEvent):
        raw_segments = self._get_raw_message_segments(event)
        for segment in raw_segments:
            if not isinstance(segment, dict) or segment.get("type") != "reply":
                continue
            data = segment.get("data") or {}
            if not isinstance(data, dict):
                continue
            for key in ("url", "file", "path"):
                image_file = data.get(key)
                if self._has_value(image_file):
                    return image_file
        return None

    def _get_first_image_file_from_raw_segments(self, event: AiocqhttpMessageEvent):
        raw_segments = self._get_raw_message_segments(event)
        for segment in raw_segments:
            if not isinstance(segment, dict) or segment.get("type") != "image":
                continue
            data = segment.get("data") or {}
            if not isinstance(data, dict):
                continue
            for key in ("url", "file", "path"):
                image_file = data.get(key)
                if self._has_value(image_file):
                    return image_file
        return None

    def _get_raw_message_segments(self, event: AiocqhttpMessageEvent) -> list:
        message_obj = getattr(event, "message_obj", None)
        raw_message = getattr(message_obj, "raw_message", None)
        raw_segments = getattr(raw_message, "message", None)
        return raw_segments if isinstance(raw_segments, list) else []

    def _has_value(self, value) -> bool:
        return value is not None and value != ""

    async def napcat_arksharegroup_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        send_group_id: int = None,
        send_user_id: int = None,
    ):
        """获取群分享 Ark 卡片并发送到群聊或私聊，适合分享群名片、群邀请和群资料卡片

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    send_group_id(int): 可选，要发送到的群号。和 send_user_id 都不填时默认发送到当前会话。
    send_user_id(int): 可选，要发送到的用户 QQ。和 send_group_id 都不填时默认发送到当前会话。

Returns:
    str: 返回 Ark 获取结果和自动发送结果的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_ark_share_and_send(
            event, 'ArkShareGroup', payload, send_group_id, send_user_id
        )

    async def napcat_arksharepeer_tool(
        self,
        event: AstrMessageEvent,
        phone_number: str,
        group_id: int = None,
        user_id: int = None,
        phoneNumber: str = None,
        send_group_id: int = None,
        send_user_id: int = None,
    ):
        """获取用户推荐 Ark 卡片并发送到群聊或私聊，适合分享联系人推荐、好友名片和用户邀请卡片

Args:
    phone_number(str): 必填，手机号。
    group_id(int): 可选，和user_id二选一。
    phoneNumber(str): 可选，对方手机号。
    user_id(int): 可选，和user_id二选一。
    send_group_id(int): 可选，要发送到的群号。和 send_user_id 都不填时默认发送到当前会话。
    send_user_id(int): 可选，要发送到的用户 QQ。和 send_group_id 都不填时默认发送到当前会话。

Returns:
    str: 返回 Ark 获取结果和自动发送结果的 JSON 字符串。"""
        payload: dict = {}
        if phone_number is not None:
            payload['phone_number'] = phone_number
        if group_id is not None:
            payload['group_id'] = group_id
        if phoneNumber is not None:
            payload['phoneNumber'] = phoneNumber
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_ark_share_and_send(
            event, 'ArkSharePeer', payload, send_group_id, send_user_id
        )

    # napcat_tool: napcat_bot_exit
    async def napcat_bot_exit_tool(
        self,
        event: AstrMessageEvent,
    ):
        """让当前 QQ 账号退出登录，适合主动下线、切换账号或关闭当前机器人会话

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'bot_exit', payload)

    # napcat_tool: napcat_can_send_image
    async def napcat_can_send_image_tool(
        self,
        event: AstrMessageEvent,
    ):
        """检查当前账号是否支持发送图片，适合发送图片前检测图片消息能力

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'can_send_image', payload)

    # napcat_tool: napcat_can_send_record
    async def napcat_can_send_record_tool(
        self,
        event: AstrMessageEvent,
    ):
        """检查当前账号是否支持发送语音，适合发送语音、录音或音频消息前检测能力

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'can_send_record', payload)

    # napcat_tool: napcat_cancel_group_todo
    async def napcat_cancel_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        message_seq: int = None,
    ):
        """取消指定消息关联的群待办，适合撤销群内待办、取消提醒或移除待办状态

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'cancel_group_todo', payload)

    # napcat_tool: napcat_cancel_online_file
    async def napcat_cancel_online_file_tool(
        self,
        event: AstrMessageEvent,
        msg_id: str,
        user_id: int = None,
    ):
        """取消在线文件传输或接收，适合中止文件上传、下载或在线文件任务

Args:
    msg_id(str): 必填，消息 ID。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if msg_id is not None:
            payload['msg_id'] = msg_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'cancel_online_file', payload)

    # napcat_tool: napcat_check_url_safely
    async def napcat_check_url_safely_tool(
        self,
        event: AstrMessageEvent,
        url: str,
    ):
        """检测指定 URL 的安全等级，适合打开链接、分享网页或处理外部地址前做安全检查

Args:
    url(str): 必填，要检查的 URL。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if url is not None:
            payload['url'] = url
        return await self._call_napcat_api(event, 'check_url_safely', payload)

    # napcat_tool: napcat_clean_cache
    async def napcat_clean_cache_tool(
        self,
        event: AstrMessageEvent,
    ):
        """清理 NapCat 缓存数据，适合释放缓存空间、刷新临时状态或排查缓存异常

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'clean_cache', payload)

    # napcat_tool: napcat_clean_stream_temp_file
    async def napcat_clean_stream_temp_file_tool(
        self,
        event: AstrMessageEvent,
    ):
        """清理流式下载产生的临时文件，适合释放下载缓存和删除语音、图片、文件流残留

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'clean_stream_temp_file', payload)

    # napcat_tool: napcat_click_inline_keyboard_button
    async def napcat_click_inline_keyboard_button_tool(
        self,
        event: AstrMessageEvent,
        bot_appid: str,
        button_id: str,
        callback_data: str,
        msg_seq: int,
        group_id: int = None,
    ):
        """点击指定消息中的内联键盘按钮，适合模拟按钮交互、触发机器人回调或操作内联菜单

Args:
    bot_appid(str): 必填，机器人AppID。
    button_id(str): 必填，按钮ID。
    callback_data(str): 必填，回调数据。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    msg_seq(int): 必填，消息序列号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if bot_appid is not None:
            payload['bot_appid'] = bot_appid
        if button_id is not None:
            payload['button_id'] = button_id
        if callback_data is not None:
            payload['callback_data'] = callback_data
        payload['group_id'] = group_id
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq
        return await self._call_napcat_api(event, 'click_inline_keyboard_button', payload)

    # napcat_tool: napcat_complete_group_todo
    async def napcat_complete_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        message_seq: int = None,
    ):
        """将指定消息关联的群待办标记为完成，适合完成群提醒、任务确认或待办闭环

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'complete_group_todo', payload)

    # napcat_tool: napcat_create_collection
    async def napcat_create_collection_tool(
        self,
        event: AstrMessageEvent,
        brief: str,
        rawData: str,
    ):
        """创建新的 QQ 收藏内容，适合收藏文本、图片、语音、文件或消息内容

Args:
    brief(str): 必填，简要描述。
    rawData(str): 必填，原始数据。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if brief is not None:
            payload['brief'] = brief
        if rawData is not None:
            payload['rawData'] = rawData
        return await self._call_napcat_api(event, 'create_collection', payload)

    # napcat_tool: napcat_create_flash_task
    async def napcat_create_flash_task_tool(
        self,
        event: AstrMessageEvent,
        files: str,
        name: str = None,
        thumb_path: str = None,
    ):
        """创建闪传任务，适合准备快速上传、分享或发送大文件集合

Args:
    files(str): 必填，文件列表或单个文件路径。
    name(str): 可选，任务名称。
    thumb_path(str): 可选，缩略图路径。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if files is not None:
            payload['files'] = files
        if name is not None:
            payload['name'] = name
        if thumb_path is not None:
            payload['thumb_path'] = thumb_path
        return await self._call_napcat_api(event, 'create_flash_task', payload)

    # napcat_tool: napcat_create_group_file_folder
    async def napcat_create_group_file_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_name: str,
        group_id: int = None,
        name: str = None,
        parent_id: str = None,
    ):
        """在群文件中创建文件夹，适合整理群文件目录、分类资料或新建共享目录

Args:
    folder_name(str): 必填，文件夹名称。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    name(str): 可选，文件夹名称。
    parent_id(str): 可选，仅能为 `/`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_name is not None:
            payload['folder_name'] = folder_name
        payload['group_id'] = group_id
        if name is not None:
            payload['name'] = name
        if parent_id is not None:
            payload['parent_id'] = parent_id
        return await self._call_napcat_api(event, 'create_group_file_folder', payload)

    # napcat_tool: napcat_create_guild_role
    async def napcat_create_guild_role_tool(
        self,
        event: AstrMessageEvent,
        color: str,
        guild_id: str,
        name: str,
        independent: bool = None,
        initial_users: list = None,
    ):
        """在频道中创建角色，适合管理频道身份组、权限角色和成员分组

Args:
    color(str): 必填，颜色。
    guild_id(str): 必填，频道ID。
    name(str): 必填，角色名。
    independent(bool): 可选，未知 默认值: false。
    initial_users(list): 可选，- 默认值: string。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if color is not None:
            payload['color'] = color
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if name is not None:
            payload['name'] = name
        if independent is not None:
            payload['independent'] = independent
        if initial_users is not None:
            payload['initial_users'] = initial_users
        return await self._call_napcat_api(event, 'create_guild_role', payload)

    # napcat_tool: napcat_del_group_album_media
    async def napcat_del_group_album_media_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        lloc: str,
        group_id: int = None,
    ):
        """删除群相册中的媒体文件，适合移除群相册图片、视频或相册资源

Args:
    album_id(str): 必填，相册ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    lloc(str): 必填，媒体ID (lloc)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        payload['group_id'] = group_id
        if lloc is not None:
            payload['lloc'] = lloc
        return await self._call_napcat_api(event, 'del_group_album_media', payload)

    # napcat_tool: napcat_del_group_notice
    async def napcat_del_group_notice_tool(
        self,
        event: AstrMessageEvent,
        notice_id: str,
        group_id: int = None,
    ):
        """删除指定群公告，适合撤下群公告、清理过期通知或管理公告内容

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    notice_id(str): 必填，公告ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if notice_id is not None:
            payload['notice_id'] = notice_id
        return await self._call_napcat_api(event, '_del_group_notice', payload)

    # napcat_tool: napcat_delete_essence_msg
    async def napcat_delete_essence_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
        group_id: int = None,
        msg_random: str = None,
        msg_seq: int = None,
    ):
        """删除群精华消息，适合移除已设为精华的群消息或整理群精华列表

Args:
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    group_id(int): 可选，群号。
    msg_random(str): 可选，消息随机数。
    msg_seq(int): 可选，消息序号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        if group_id is not None:
            payload['group_id'] = group_id
        if msg_random is not None:
            payload['msg_random'] = msg_random
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq
        return await self._call_napcat_api(event, 'delete_essence_msg', payload)

    # napcat_tool: napcat_delete_friend
    async def napcat_delete_friend_tool(
        self,
        event: AstrMessageEvent,
        temp_block: bool,
        temp_both_del: bool,
        user_id: int = None,
        friend_id: str = None,
    ):
        """删除指定 QQ 好友，适合解除好友关系或清理好友列表

Args:
    temp_block(bool): 必填，是否加入黑名单。
    temp_both_del(bool): 必填，是否双向删除。
    user_id(int): 可选，用户 QQ 号。默认使用当前消息发送者的用户 ID。
    friend_id(str): 可选，好友 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if temp_block is not None:
            payload['temp_block'] = temp_block
        if temp_both_del is not None:
            payload['temp_both_del'] = temp_both_del
        payload['user_id'] = user_id
        if friend_id is not None:
            payload['friend_id'] = friend_id
        return await self._call_napcat_api(event, 'delete_friend', payload)

    # napcat_tool: napcat_delete_group_file
    async def napcat_delete_group_file_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int = None,
        busid: int = None,
    ):
        """删除指定群文件，适合清理群文件资源、移除过期附件或删除共享文件

Args:
    file_id(str): 必填，文件ID 参考 `File` 对象。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    busid(int): 可选，文件类型 参考 `File` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        payload['group_id'] = group_id
        if busid is not None:
            payload['busid'] = busid
        return await self._call_napcat_api(event, 'delete_group_file', payload)

    # napcat_tool: napcat_delete_group_folder
    async def napcat_delete_group_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_id: str,
        group_id: int = None,
        folder: str = None,
    ):
        """删除指定群文件夹，适合移除空目录、清理群文件分类或整理群文件空间

Args:
    folder_id(str): 必填，文件夹ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    folder(str): 可选，文件夹ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_id is not None:
            payload['folder_id'] = folder_id
        payload['group_id'] = group_id
        if folder is not None:
            payload['folder'] = folder
        return await self._call_napcat_api(event, 'delete_group_folder', payload)

    # napcat_tool: napcat_delete_guild_role
    async def napcat_delete_guild_role_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        role_id: str = None,
    ):
        """删除频道角色，适合移除频道身份组、权限角色或废弃角色配置

Args:
    guild_id(str): 可选，频道ID。
    role_id(str): 可选，角色ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if role_id is not None:
            payload['role_id'] = role_id
        return await self._call_napcat_api(event, 'delete_guild_role', payload)

    # napcat_tool: napcat_delete_msg
    async def napcat_delete_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
    ):
        """撤回指定消息，适合删除机器人已发送消息、撤回误发内容或清理会话消息

Args:
    message_id(int): 可选，消息 ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'delete_msg', payload)

    # napcat_tool: napcat_delete_unidirectional_friend
    async def napcat_delete_unidirectional_friend_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
    ):
        """删除单向好友，适合清理只保留在单向关系中的陌生人或历史联系人

Args:
    user_id(int): 可选，单向好友QQ号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'delete_unidirectional_friend', payload)

    # napcat_tool: napcat_do_group_album_comment
    async def napcat_do_group_album_comment_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        content: str,
        lloc: str,
        group_id: int = None,
    ):
        """给群相册内容发表评论，适合评论群相册图片、视频或媒体动态

Args:
    album_id(str): 必填，相册 ID。
    content(str): 必填，评论内容。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    lloc(str): 必填，图片 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if content is not None:
            payload['content'] = content
        payload['group_id'] = group_id
        if lloc is not None:
            payload['lloc'] = lloc
        return await self._call_napcat_api(event, 'do_group_album_comment', payload)

    # napcat_tool: napcat_dot_get_word_slices
    async def napcat_dot_get_word_slices_tool(
        self,
        event: AstrMessageEvent,
        content: str = None,
    ):
        """对中文文本进行分词，适合关键词提取、文本切分和搜索词分析

Args:
    content(str): 可选，内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if content is not None:
            payload['content'] = content
        return await self._call_napcat_api(event, '.get_word_slices', payload)

    # napcat_tool: napcat_dot_handle_quick_operation
    async def napcat_dot_handle_quick_operation_tool(
        self,
        event: AstrMessageEvent,
        context: dict,
        operation: dict,
    ):
        """执行 OneBot 快速操作，适合按事件上下文快速响应、撤回或发送复合动作

Args:
    context(dict): 必填，事件数据对象, 可做精简, 如去掉 `message` 等无用字段。
    operation(dict): 必填，快速操作对象, 例如 `{"ban": true, "reply": "请不要说脏话"}`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if context is not None:
            payload['context'] = context
        if operation is not None:
            payload['operation'] = operation
        return await self._call_napcat_api(event, '.handle_quick_operation', payload)

    # napcat_tool: napcat_dot_ocr_image
    async def napcat_dot_ocr_image_tool(
        self,
        event: AstrMessageEvent,
        image: str,
    ):
        """识别图片文字，仅 Windows 可用，适合 OCR 提取截图、图片或表情包中的文本

Args:
    image(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, '.ocr_image', payload)

    # napcat_tool: napcat_download_file
    async def napcat_download_file_tool(
        self,
        event: AstrMessageEvent,
        base64: str = None,
        headers: list = None,
        name: str = None,
        thread_count: int = None,
        url: str = None,
    ):
        """下载网络文件到本地临时目录，适合获取 URL 文件、缓存远程资源或准备后续上传发送

Args:
    base64(str): 可选，base64数据。
    headers(list): 可选，自定义请求头。
    name(str): 可选，自定义文件名称。
    thread_count(int): 可选，下载线程数。
    url(str): 可选，下载链接。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if base64 is not None:
            payload['base64'] = base64
        if headers is not None:
            payload['headers'] = headers
        if name is not None:
            payload['name'] = name
        if thread_count is not None:
            payload['thread_count'] = thread_count
        if url is not None:
            payload['url'] = url
        return await self._call_napcat_api(event, 'download_file', payload)

    # napcat_tool: napcat_download_file_image_stream
    async def napcat_download_file_image_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None,
    ):
        """下载图片文件流，适合按 file_id、URL 或路径获取图片二进制流、图片缓存和后续转发素材

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'download_file_image_stream', payload)

    # napcat_tool: napcat_download_file_record_stream
    async def napcat_download_file_record_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None,
        out_format: str = None,
    ):
        """下载语音文件流，适合获取语音、录音、音频文件的二进制流或临时缓存素材

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。
    out_format(str): 可选，输出格式。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        if out_format is not None:
            payload['out_format'] = out_format
        return await self._call_napcat_api(event, 'download_file_record_stream', payload)

    # napcat_tool: napcat_download_file_stream
    async def napcat_download_file_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None,
    ):
        """以流式方式下载网络或本地文件，适合大文件、临时文件、图片、语音和附件流式获取

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'download_file_stream', payload)

    # napcat_tool: napcat_download_fileset
    async def napcat_download_fileset_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
    ):
        """下载文件集，适合批量获取闪传或文件集合中的多个文件、附件包和资源集合

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'download_fileset', payload)

    # napcat_tool: napcat_fetch_custom_face
    async def napcat_fetch_custom_face_tool(
        self,
        event: AstrMessageEvent,
        count: int,
    ):
        """获取账号收藏表情列表，适合查询自定义表情、收藏表情包和可发送表情资源

Args:
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'fetch_custom_face', payload)

    # napcat_tool: napcat_fetch_emoji_like
    async def napcat_fetch_emoji_like_tool(
        self,
        event: AstrMessageEvent,
        cookie: str,
        count: int,
        emojiId: str,
        emojiType: str,
        message_id: int = None,
    ):
        """获取单个表情点赞详情，适合查看某条消息表情回应、点赞用户和 Emoji 互动信息

Args:
    cookie(str): 必填，分页Cookie。
    count(int): 必填，获取数量。
    emojiId(str): 必填，表情ID。
    emojiType(str): 必填，表情类型。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if cookie is not None:
            payload['cookie'] = cookie
        if count is not None:
            payload['count'] = count
        if emojiId is not None:
            payload['emojiId'] = emojiId
        if emojiType is not None:
            payload['emojiType'] = emojiType
        payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'fetch_emoji_like', payload)

    async def napcat_forward_single_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
        message_type: str = None,
        group_id: int = None,
        user_id: int = None,
    ):
        """单条消息快速转发到群聊或私聊，只处理一个 message_id，不适合批量聊天记录或多条消息合并转发

Args:
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    message_type(str): 可选，目标类型，支持 `group` 或 `private`；不填时优先根据 group_id/user_id 和当前会话判断。
    group_id(int): 可选，目标群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会转为私聊转发。
    user_id(int): 可选，目标用户QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        normalized_type = (message_type or "").lower()
        if normalized_type in {"group", "guild"} or group_id is not None:
            payload: dict = {'message_id': message_id, 'group_id': group_id}
            if user_id is not None:
                payload['user_id'] = user_id
            return await self._call_napcat_api(
                event, 'forward_group_single_msg', payload
            )

        if normalized_type == "private" or user_id is not None:
            payload = {'message_id': message_id, 'user_id': user_id}
            if group_id is not None:
                payload['group_id'] = group_id
            return await self._call_napcat_api(
                event, 'forward_friend_single_msg', payload
            )

        if self._get_current_group_id_or_none(event) is not None:
            return await self._call_napcat_api(
                event,
                'forward_group_single_msg',
                {'message_id': message_id, 'group_id': group_id},
            )
        return await self._call_napcat_api(
            event,
            'forward_friend_single_msg',
            {'message_id': message_id, 'user_id': user_id},
        )

    async def napcat_forward_friend_single_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
        user_id: int = None,
        group_id: int = None,
    ):
        """将指定消息转发到私聊好友，适合把群消息、历史消息或当前会话消息单独转发给用户

Args:
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    user_id(int): 可选，目标用户QQ。默认使用当前消息发送者的用户 ID。
    group_id(int): 可选，目标群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'forward_friend_single_msg', payload)

    async def napcat_forward_group_single_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        user_id: int = None,
    ):
        """将指定消息转发到群聊，适合把私聊消息、历史消息或当前会话消息转发到指定群

Args:
    group_id(int): 可选，目标群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    user_id(int): 可选，目标用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'forward_group_single_msg', payload)

    async def napcat_friend_poke_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
        group_id: int = None,
        target_id: int = None,
    ):
        """在私聊或群聊中发送戳一戳，适合提醒用户、轻互动、拍一拍和 poke 动作

Args:
    user_id(int): 可选，要戳的 QQ 号。默认使用当前消息发送者的用户 ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；私聊中不传则按私聊戳一戳处理。
    target_id(int): 可选，兼容别名，等同于 user_id；当 user_id 未提供时会作为要戳的 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is None and target_id is not None:
            user_id = target_id
        payload['user_id'] = user_id
        if group_id is None:
            group_id = self._get_current_group_id_or_none(event)
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'friend_poke', payload)

    # napcat_tool: napcat_get_ai_characters
    async def napcat_get_ai_characters_tool(
        self,
        event: AstrMessageEvent,
        chat_type: str,
        group_id: int = None,
    ):
        """获取群聊可用 AI 角色列表，适合查询群语音角色、AI 声线和可用角色 ID

Args:
    chat_type(str): 必填，1 or 2?。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chat_type is not None:
            payload['chat_type'] = chat_type
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_ai_characters', payload)

    # napcat_tool: napcat_get_ai_record
    async def napcat_get_ai_record_tool(
        self,
        event: AstrMessageEvent,
        character: str,
        text: str,
        group_id: int = None,
    ):
        """把文本转换为 AI 角色语音并获取语音 URL，适合生成群 AI 语音、TTS 和角色配音

Args:
    character(str): 必填，character_id。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    text(str): 必填，语音文本内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if character is not None:
            payload['character'] = character
        payload['group_id'] = group_id
        if text is not None:
            payload['text'] = text
        return await self._call_napcat_api(event, 'get_ai_record', payload)

    # napcat_tool: napcat_get_clientkey
    async def napcat_get_clientkey_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取当前登录账号 ClientKey，适合调用 QQ Web 接口、鉴权接口和需要客户端密钥的能力

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_clientkey', payload)

    # napcat_tool: napcat_get_collection_list
    async def napcat_get_collection_list_tool(
        self,
        event: AstrMessageEvent,
        category: str,
        count: int,
    ):
        """获取 QQ 收藏列表，适合查询收藏文本、图片、语音、文件和历史收藏内容

Args:
    category(str): 必填，分类ID。
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if category is not None:
            payload['category'] = category
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_collection_list', payload)

    # napcat_tool: napcat_get_cookies
    async def napcat_get_cookies_tool(
        self,
        event: AstrMessageEvent,
        domain: str,
    ):
        """获取指定域名 Cookies，适合访问 QQ 相关 Web 服务、登录态接口和需要 Cookie 的请求

Args:
    domain(str): 必填，需要获取 cookies 的域名 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if domain is not None:
            payload['domain'] = domain
        return await self._call_napcat_api(event, 'get_cookies', payload)

    # napcat_tool: napcat_get_credentials
    async def napcat_get_credentials_tool(
        self,
        event: AstrMessageEvent,
        domain: str,
    ):
        """获取 QQ 接口凭证，适合一次性取得 cookies、csrf token、clientkey 等鉴权信息

Args:
    domain(str): 必填，需要获取 cookies 的域名 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if domain is not None:
            payload['domain'] = domain
        return await self._call_napcat_api(event, 'get_credentials', payload)

    # napcat_tool: napcat_get_csrf_token
    async def napcat_get_csrf_token_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取 CSRF Token，适合调用需要 bkn、gtk 或防跨站令牌的 QQ Web 接口

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_csrf_token', payload)

    # napcat_tool: napcat_get_doubt_friends_add_request
    async def napcat_get_doubt_friends_add_request_tool(
        self,
        event: AstrMessageEvent,
        count: int,
    ):
        """获取可疑好友申请列表，适合查看风控拦截、异常好友请求和待处理加好友通知

Args:
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_doubt_friends_add_request', payload)

    # napcat_tool: napcat_get_emoji_likes
    async def napcat_get_emoji_likes_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        emoji_id: int,
        message_id: int = None,
        group_id: int = None,
        emoji_type: int = None,
    ):
        """获取消息表情点赞列表，适合查询某条消息收到的 Emoji 回应、点赞统计和互动用户

Args:
    count(int): 必填，数量，0代表全部。
    emoji_id(int): 必填，表情ID。
    message_id(int): 可选，消息ID，可以传递长ID或短ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    emoji_type(int): 可选，表情类型。
    group_id(int): 可选，群号，短ID可不传。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if emoji_id is not None:
            payload['emoji_id'] = emoji_id
        payload['message_id'] = message_id
        if emoji_type is not None:
            payload['emoji_type'] = emoji_type
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_emoji_likes', payload)

    # napcat_tool: napcat_get_essence_msg_list
    async def napcat_get_essence_msg_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群精华消息列表，适合查看群内已设精华的消息、重要内容和精华记录

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_essence_msg_list', payload)

    # napcat_tool: napcat_get_file
    async def napcat_get_file_tool(
        self,
        event: AstrMessageEvent,
        file: str = None,
        file_id: str = None,
    ):
        """获取文件详情和下载路径，适合根据 file_id 查询文件名、大小、URL 和本地缓存位置

Args:
    file(str): 可选，文件路径、URL或Base64。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_file', payload)

    # napcat_tool: napcat_get_fileset_id
    async def napcat_get_fileset_id_tool(
        self,
        event: AstrMessageEvent,
        share_code: str,
    ):
        """获取文件集 ID，适合根据文件、闪传任务或资源集合定位 fileset 标识

Args:
    share_code(str): 必填，分享码或分享链接。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if share_code is not None:
            payload['share_code'] = share_code
        return await self._call_napcat_api(event, 'get_fileset_id', payload)

    # napcat_tool: napcat_get_fileset_info
    async def napcat_get_fileset_info_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
    ):
        """获取文件集信息，适合查询文件集合元数据、文件数量、资源状态和下载准备信息

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_fileset_info', payload)

    # napcat_tool: napcat_get_flash_file_list
    async def napcat_get_flash_file_list_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
    ):
        """获取闪传文件列表，适合查看快速传输任务中的文件、附件集合和可下载资源

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_flash_file_list', payload)

    # napcat_tool: napcat_get_flash_file_url
    async def napcat_get_flash_file_url_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
        file_index: int = None,
        file_name: str = None,
    ):
        """获取闪传文件下载链接，适合根据闪传文件 ID 取得 URL、下载地址或临时访问链接

Args:
    fileset_id(str): 必填，文件集 ID。
    file_index(int): 可选，文件索引。
    file_name(str): 可选，文件名。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        if file_index is not None:
            payload['file_index'] = file_index
        if file_name is not None:
            payload['file_name'] = file_name
        return await self._call_napcat_api(event, 'get_flash_file_url', payload)

    # napcat_tool: napcat_get_forward_msg
    async def napcat_get_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
        id: str = None,
    ):
        """获取合并转发消息内容，适合展开聊天记录、转发节点、合并消息和转发详情

Args:
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    id(str): 可选，合并转发 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        if id is not None:
            payload['id'] = id
        return await self._call_napcat_api(event, 'get_forward_msg', payload)

    # napcat_tool: napcat_get_friend_list
    async def napcat_get_friend_list_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool,
    ):
        """获取当前账号好友列表，适合查询 QQ 好友、联系人、用户 ID 和好友昵称备注

Args:
    no_cache(bool): 必填，是否不使用缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_friend_list', payload)

    async def napcat_get_friend_msg_history_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        disable_get_url: bool,
        parse_mult_msg: bool,
        quick_reply: bool,
        reverse_order: bool,
        reverseOrder: bool,
        user_id: int = None,
        message_seq: int = None,
    ):
        """获取指定好友历史聊天记录，适合查询私聊消息、上下文记录和近期会话内容

Args:
    count(int): 必填，获取消息数量。
    disable_get_url(bool): 必填，是否禁用获取URL。
    parse_mult_msg(bool): 必填，是否解析合并消息。
    quick_reply(bool): 必填，是否快速回复。
    reverse_order(bool): 必填，是否反向排序。
    reverseOrder(bool): 必填，是否反向排序(旧版本兼容)。
    user_id(int): 可选，用户QQ。默认使用当前消息发送者的用户 ID。
    message_seq(int): 可选，起始消息序号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if disable_get_url is not None:
            payload['disable_get_url'] = disable_get_url
        if parse_mult_msg is not None:
            payload['parse_mult_msg'] = parse_mult_msg
        if quick_reply is not None:
            payload['quick_reply'] = quick_reply
        if reverse_order is not None:
            payload['reverse_order'] = reverse_order
        if reverseOrder is not None:
            payload['reverseOrder'] = reverseOrder
        payload['user_id'] = user_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'get_friend_msg_history', payload)

    # napcat_tool: napcat_get_msg_history
    async def napcat_get_msg_history_tool(
        self,
        event: AstrMessageEvent,
        count: int = 20,
        message_type: str = None,
        group_id: int = None,
        user_id: int = None,
        message_seq: int = None,
        disable_get_url: bool = True,
        parse_mult_msg: bool = True,
        quick_reply: bool = True,
        reverse_order: bool = True,
        reverseOrder: bool = True,
    ):
        """获取群聊或私聊历史聊天记录，适合查询聊天上下文、近期消息、message_id 和合并转发前选取消息

Args:
    count(int): 可选，获取消息数量，默认 20。
    message_type(str): 可选，历史类型，支持 `group` 或 `private`；不填时优先按 group_id/user_id 和当前会话判断。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会按私聊历史处理。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。
    message_seq(int): 可选，起始消息序号；不填时使用 0 获取最近消息，避免 NapCat 旧版本收到 undefined。
    disable_get_url(bool): 可选，是否禁用获取 URL，默认 true。
    parse_mult_msg(bool): 可选，是否解析合并消息，默认 true。
    quick_reply(bool): 可选，是否快速回复，默认 true。
    reverse_order(bool): 可选，是否反向排序，默认 true。
    reverseOrder(bool): 可选，是否反向排序旧字段，默认 true。

Returns:
    str: 返回 API 响应的 JSON 字符串，通常包含 data.messages；这些消息的 message_id 可传给 napcat_send_forward_msg 打包转发。"""
        normalized_type = (message_type or "").lower()
        payload: dict = {
            "count": count,
            "disable_get_url": disable_get_url,
            "parse_mult_msg": parse_mult_msg,
            "quick_reply": quick_reply,
            "reverse_order": reverse_order,
            "reverseOrder": reverseOrder,
        }
        payload["message_seq"] = 0 if message_seq is None else message_seq

        if normalized_type in {"group", "guild"} or group_id is not None:
            payload["group_id"] = group_id
            return await self._call_napcat_api(event, "get_group_msg_history", payload)

        if normalized_type in {"private", "friend"} or user_id is not None:
            payload["user_id"] = user_id
            return await self._call_napcat_api(event, "get_friend_msg_history", payload)

        if self._get_current_group_id_or_none(event) is not None:
            payload["group_id"] = group_id
            return await self._call_napcat_api(event, "get_group_msg_history", payload)

        payload["user_id"] = user_id
        return await self._call_napcat_api(event, "get_friend_msg_history", payload)

    # napcat_tool: napcat_get_friends_with_category
    async def napcat_get_friends_with_category_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取好友分组和分组内好友列表，适合查询联系人分类、好友类别和分组成员

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_friends_with_category', payload)

    # napcat_tool: napcat_get_group_album_media_list
    async def napcat_get_group_album_media_list_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        attach_info: str,
        group_id: int = None,
    ):
        """获取群相册媒体列表，适合查询群相册图片、视频、相册资源和上传前选择相册

Args:
    album_id(str): 必填，相册ID。
    attach_info(str): 必填，附加信息（用于分页）。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if attach_info is not None:
            payload['attach_info'] = attach_info
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_album_media_list', payload)

    # napcat_tool: napcat_get_group_at_all_remain
    async def napcat_get_group_at_all_remain_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群 @全体成员 剩余次数，适合发送全体提醒前检查额度、次数和权限限制

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_at_all_remain', payload)

    # napcat_tool: napcat_get_group_detail_info
    async def napcat_get_group_detail_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群详细资料，适合查询群人数、最大人数、群名称、群资料和扩展统计信息

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_detail_info', payload)

    # napcat_tool: napcat_get_group_file_system_info
    async def napcat_get_group_file_system_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群文件系统空间状态，适合查询群文件容量、已用空间、文件数量和存储限制

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_file_system_info', payload)

    # napcat_tool: napcat_get_group_file_url
    async def napcat_get_group_file_url_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int = None,
        busid: int = None,
    ):
        """获取群文件下载链接，适合根据群文件 ID、busid 或路径下载群共享文件

Args:
    file_id(str): 必填，文件ID 参考 `File` 对象。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    busid(int): 可选，文件类型 参考 `File` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        payload['group_id'] = group_id
        if busid is not None:
            payload['busid'] = busid
        return await self._call_napcat_api(event, 'get_group_file_url', payload)

    # napcat_tool: napcat_get_group_files_by_folder
    async def napcat_get_group_files_by_folder_tool(
        self,
        event: AstrMessageEvent,
        file_count: int,
        group_id: int = None,
        folder: str = None,
        folder_id: str = None,
    ):
        """获取群文件夹内文件列表，适合浏览群文件子目录、文件夹内容和共享资料目录

Args:
    file_count(int): 必填，一次性获取的文件数量。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    folder(str): 可选，和 folder_id 二选一。
    folder_id(str): 可选，文件夹ID 参考 `Folder` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_count is not None:
            payload['file_count'] = file_count
        payload['group_id'] = group_id
        if folder is not None:
            payload['folder'] = folder
        if folder_id is not None:
            payload['folder_id'] = folder_id
        return await self._call_napcat_api(event, 'get_group_files_by_folder', payload)

    # napcat_tool: napcat_get_group_honor_info
    async def napcat_get_group_honor_info_tool(
        self,
        event: AstrMessageEvent,
        type: str = None,
        group_id: int = None,
    ):
        """获取群荣誉信息，适合查询龙王、群聊之火、快乐源泉、活跃成员和群荣誉榜

Args:
    type(str): 可选，荣誉类型，可选 all、talkative、performer、legend、strong_newbie、emotion。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if type is not None:
            payload['type'] = type
        return await self._call_napcat_api(event, 'get_group_honor_info', payload)

    # napcat_tool: napcat_get_group_ignore_add_request
    async def napcat_get_group_ignore_add_request_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取被忽略的加群请求，适合查看群申请拦截、已忽略入群请求和待复查通知

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_group_ignore_add_request', payload)

    # napcat_tool: napcat_get_group_ignored_notifies
    async def napcat_get_group_ignored_notifies_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取被忽略的群通知，适合查看入群申请、群邀请、系统通知和忽略记录

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_group_ignored_notifies', payload)

    # napcat_tool: napcat_get_group_info
    async def napcat_get_group_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        no_cache: bool = None,
    ):
        """获取群基本信息，适合查询群号、群名称、成员数量和当前会话群资料

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_info', payload)

    # napcat_tool: napcat_get_group_info_ex
    async def napcat_get_group_info_ex_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群扩展信息，适合查询群详细资料、等级、人数、头像、标签和额外群属性

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_info_ex', payload)

    # napcat_tool: napcat_get_group_list
    async def napcat_get_group_list_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool,
    ):
        """获取当前账号群聊列表，适合查询已加入群、群号、群名称和群会话清单

Args:
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_list', payload)

    # napcat_tool: napcat_get_group_member_info
    async def napcat_get_group_member_info_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool,
        group_id: int = None,
        user_id: int = None,
    ):
        """获取群成员信息，适合查询指定成员昵称、群名片、角色、禁言状态和入群时间

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。
    user_id(int): 可选，QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_group_member_info', payload)

    # napcat_tool: napcat_get_group_member_list
    async def napcat_get_group_member_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        no_cache: bool = None,
    ):
        """获取群成员列表，适合枚举群内成员、管理员、群主、群名片和成员基础资料

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_member_list', payload)

    async def napcat_get_group_msg_history_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        disable_get_url: bool,
        parse_mult_msg: bool,
        quick_reply: bool,
        reverse_order: bool,
        reverseOrder: bool,
        group_id: int = None,
        message_seq: int = None,
    ):
        """获取群历史聊天记录，适合查询群消息上下文、近期记录和指定 message_seq 附近消息

Args:
    count(int): 必填，获取消息数量。
    disable_get_url(bool): 必填，是否禁用获取URL。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    parse_mult_msg(bool): 必填，是否解析合并消息。
    quick_reply(bool): 必填，是否快速回复。
    reverse_order(bool): 必填，是否反向排序。
    reverseOrder(bool): 必填，是否反向排序(旧版本兼容)。
    message_seq(int): 可选，起始消息序号, 可通过 `get_msg` 获得。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if disable_get_url is not None:
            payload['disable_get_url'] = disable_get_url
        payload['group_id'] = group_id
        if parse_mult_msg is not None:
            payload['parse_mult_msg'] = parse_mult_msg
        if quick_reply is not None:
            payload['quick_reply'] = quick_reply
        if reverse_order is not None:
            payload['reverse_order'] = reverse_order
        if reverseOrder is not None:
            payload['reverseOrder'] = reverseOrder
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'get_group_msg_history', payload)

    # napcat_tool: napcat_get_group_notice
    async def napcat_get_group_notice_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群公告列表，适合查看群通知、公告内容、发布者和历史公告记录

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, '_get_group_notice', payload)

    # napcat_tool: napcat_get_group_root_files
    async def napcat_get_group_root_files_tool(
        self,
        event: AstrMessageEvent,
        file_count: int,
        group_id: int = None,
    ):
        """获取群文件根目录列表，适合浏览群文件首页、顶层文件夹和共享文件入口

Args:
    file_count(int): 必填，文件数量。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_count is not None:
            payload['file_count'] = file_count
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_root_files', payload)

    # napcat_tool: napcat_get_group_shut_list
    async def napcat_get_group_shut_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """获取群禁言列表，适合查询被禁言成员、禁言剩余时间和群管控状态

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_shut_list', payload)

    # napcat_tool: napcat_get_group_system_msg
    async def napcat_get_group_system_msg_tool(
        self,
        event: AstrMessageEvent,
        count: int,
    ):
        """获取群系统消息，适合查看加群申请、邀请通知、管理事件和待处理群通知

Args:
    count(int): 必填，获取的消息数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_group_system_msg', payload)

    # napcat_tool: napcat_get_guild_channel_list
    async def napcat_get_guild_channel_list_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        no_cache: bool = None,
    ):
        """获取频道子频道列表，适合查询频道服务器下的文字频道、语音频道和频道 ID

Args:
    guild_id(str): 可选，频道ID。
    no_cache(bool): 可选，是否无视缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_guild_channel_list', payload)

    # napcat_tool: napcat_get_guild_list
    async def napcat_get_guild_list_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取频道列表，适合查询当前账号加入的频道、频道服务器和 guild ID

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_guild_list', payload)

    # napcat_tool: napcat_get_guild_member_list
    async def napcat_get_guild_member_list_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        next_token: str = None,
    ):
        """获取频道成员列表，适合枚举频道用户、成员昵称、角色和频道内身份信息

Args:
    guild_id(str): 可选，频道ID。
    next_token(str): 可选，翻页Token。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if next_token is not None:
            payload['next_token'] = next_token
        return await self._call_napcat_api(event, 'get_guild_member_list', payload)

    # napcat_tool: napcat_get_guild_member_profile
    async def napcat_get_guild_member_profile_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
        guild_id: str = None,
    ):
        """获取频道成员详细资料，适合查询指定频道用户的昵称、头像、角色、身份和成员档案

Args:
    guild_id(str): 可选，频道ID。
    user_id(int): 可选，用户ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_guild_member_profile', payload)

    # napcat_tool: napcat_get_guild_meta_by_guest
    async def napcat_get_guild_meta_by_guest_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
    ):
        """以访客视角获取频道元数据，适合查询频道名称、图标、简介、公开资料和 guild 信息

Args:
    guild_id(str): 可选，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_guild_meta_by_guest', payload)

    # napcat_tool: napcat_get_guild_msg
    async def napcat_get_guild_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
        no_cache: bool = None,
    ):
        """获取频道消息详情，适合按频道消息 ID 查询子频道聊天内容、发送者和消息结构

Args:
    message_id(int): 可选，频道消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: false。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_guild_msg', payload)

    # napcat_tool: napcat_get_guild_roles
    async def napcat_get_guild_roles_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str,
    ):
        """获取频道角色列表，适合查询频道身份组、权限角色、角色 ID 和成员分组配置

Args:
    guild_id(str): 必填，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_guild_roles', payload)

    # napcat_tool: napcat_get_guild_service_profile
    async def napcat_get_guild_service_profile_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取频道服务资料，适合查询频道服务号、机器人服务信息和频道侧资料配置

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_guild_service_profile', payload)

    # napcat_tool: napcat_get_image
    async def napcat_get_image_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        file_id: str = None,
    ):
        """获取图片信息和本地路径，适合根据 file_id 查询图片 URL、缓存路径、尺寸和下载素材

Args:
    file(str): 必填，收到的图片文件名（消息段的 `file` 参数），如 `6B4DE3DFD1BD271E3297859D41C530F5.jpg`。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_image', payload)

    # napcat_tool: napcat_get_login_info
    async def napcat_get_login_info_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取当前登录账号信息，适合查询机器人 QQ 号、昵称、账号资料和登录身份

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_login_info', payload)

    # disabled napcat_tool: napcat_get_mini_app_ark
    # async def napcat_get_mini_app_ark_tool(
    #     self,
    #     event: AstrMessageEvent,
    # ):
    #     """获取小程序 Ark
    #
    # Args:
    #     无接口参数。
    #
    # Returns:
    #     str: 返回 API 响应的 JSON 字符串。"""
    #     payload: dict = {}
    #     return await self._call_napcat_api(event, 'get_mini_app_ark', payload)

    # napcat_tool: napcat_get_model_show
    async def napcat_get_model_show_tool(
        self,
        event: AstrMessageEvent,
        model: str,
    ):
        """获取在线机型展示信息，适合查询当前账号在线设备、客户端机型和可展示设备名称

Args:
    model(str): 必填，模型名称。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if model is not None:
            payload['model'] = model
        return await self._call_napcat_api(event, '_get_model_show', payload)

    # napcat_tool: napcat_get_msg
    async def napcat_get_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
    ):
        """根据消息 ID 获取消息详情，适合查询原始消息内容、发送者、群号、私聊和消息段结构

Args:
    message_id(int): 可选，消息 ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'get_msg', payload)

    # napcat_tool: napcat_get_online_clients
    async def napcat_get_online_clients_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool = None,
    ):
        """获取当前账号在线客户端列表，适合查询手机、电脑、平板等登录设备和在线状态

Args:
    no_cache(bool): 可选，是否无视缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_online_clients', payload)

    # napcat_tool: napcat_get_online_file_msg
    async def napcat_get_online_file_msg_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
    ):
        """获取在线文件消息详情，适合查询在线传输文件、文件名、大小、发送者和接收状态

Args:
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_online_file_msg', payload)

    # napcat_tool: napcat_get_private_file_url
    async def napcat_get_private_file_url_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
    ):
        """获取私聊文件下载链接，适合根据私聊文件 ID 查询 URL、文件名和临时下载地址

Args:
    file_id(str): 必填，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_private_file_url', payload)

    # napcat_tool: napcat_get_profile_like
    async def napcat_get_profile_like_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        start: int,
        user_id: int = None,
    ):
        """获取用户资料卡点赞列表，适合查询谁赞过资料卡、点赞用户和个人主页互动记录

Args:
    count(int): 必填，获取数量。
    start(int): 必填，起始位置。
    user_id(int): 可选，指定用户，不填为获取所有。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if start is not None:
            payload['start'] = start
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_profile_like', payload)

    # napcat_tool: napcat_get_qun_album_list
    async def napcat_get_qun_album_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        attach_info: str = None,
    ):
        """获取群相册列表，适合查询群相册 ID、相册名称、图片视频集合和上传目标相册

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    attach_info(str): 可选，附加信息（用于分页，从上一次返回结果中获取）。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if attach_info is not None:
            payload['attach_info'] = attach_info
        return await self._call_napcat_api(event, 'get_qun_album_list', payload)

    # napcat_tool: napcat_get_recent_contact
    async def napcat_get_recent_contact_tool(
        self,
        event: AstrMessageEvent,
        count: int,
    ):
        """获取最近联系人会话列表，适合查询最近私聊、群聊、最新消息和会话入口

Args:
    count(int): 必填，获取的数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_recent_contact', payload)

    # napcat_tool: napcat_get_record
    async def napcat_get_record_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        out_format: str,
        file_id: str = None,
    ):
        """获取语音文件信息并转换格式，适合根据 file_id 查询语音路径、URL、时长和音频格式

Args:
    file(str): 必填，收到的语音文件名（消息段的 `file` 参数）, 如 `0B38145AA44505000B38145AA4450500.silk`。
    out_format(str): 必填，要转换到的格式, 目前支持 `mp3`、`amr`、`wma`、`m4a`、`spx`、`ogg`、`wav`、`flac`。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if out_format is not None:
            payload['out_format'] = out_format
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_record', payload)

    # napcat_tool: napcat_get_rkey
    async def napcat_get_rkey_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取资源访问 rkey，适合生成图片、语音、文件等资源链接所需的临时访问密钥

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_rkey', payload)

    # napcat_tool: napcat_get_rkey_server
    async def napcat_get_rkey_server_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取 RKey 服务器信息，适合查询资源签名服务、下载鉴权服务和 rkey 生成节点

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_rkey_server', payload)

    async def napcat_get_robot_uin_range_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取机器人 UIN 范围，适合查询账号号段、机器人账号范围和协议侧 UIN 限制

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_robot_uin_range', payload)

    # napcat_tool: napcat_get_share_link
    async def napcat_get_share_link_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
    ):
        """获取文件分享链接，适合为文件、群文件或私聊文件生成可分享 URL 和外部访问地址

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_share_link', payload)

    # napcat_tool: napcat_get_status
    async def napcat_get_status_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取 NapCat 运行状态，适合检查机器人在线、连接状态、是否正常运行和健康检查

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_status', payload)

    # napcat_tool: napcat_get_stranger_info
    async def napcat_get_stranger_info_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool,
        user_id: int = None,
    ):
        """获取陌生人账号信息，适合查询非好友用户昵称、头像、性别、年龄和公开资料

Args:
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。
    user_id(int): 可选，用户QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_stranger_info', payload)

    # napcat_tool: napcat_get_topic_channel_feeds
    async def napcat_get_topic_channel_feeds_tool(
        self,
        event: AstrMessageEvent,
        channel_id: str = None,
        guild_id: str = None,
    ):
        """获取话题频道帖子列表，适合查询频道帖子、动态、话题 feed 和内容流

Args:
    channel_id(str): 可选，子频道ID。
    guild_id(str): 可选，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if channel_id is not None:
            payload['channel_id'] = channel_id
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_topic_channel_feeds', payload)

    # napcat_tool: napcat_get_unidirectional_friend_list
    async def napcat_get_unidirectional_friend_list_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取单向好友列表，适合查询只保留单向关系的用户、陌生联系人和待清理好友

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_unidirectional_friend_list', payload)

    # napcat_tool: napcat_get_version_info
    async def napcat_get_version_info_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取 NapCat 和协议版本信息，适合查询版本号、实现名称、兼容性和运行环境信息

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_version_info', payload)

    async def napcat_group_poke_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        user_id: int = None,
        target_id: int = None,
    ):
        """在群聊中发送戳一戳，适合群内提醒成员、拍一拍、poke 和轻互动动作

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，要戳的 QQ 号。默认使用当前消息发送者的用户 ID。
    target_id(int): 可选，兼容别名，等同于 user_id；当 user_id 未提供时会作为要戳的 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is None and target_id is not None:
            user_id = target_id
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'group_poke', payload)

    # napcat_tool: napcat_mark_all_as_read
    async def napcat_mark_all_as_read_tool(
        self,
        event: AstrMessageEvent,
    ):
        """标记所有会话消息为已读，适合清空未读数、批量已读和同步消息阅读状态

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, '_mark_all_as_read', payload)

    async def napcat_mark_group_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        user_id: int = None,
    ):
        """标记指定群消息为已读，适合清除群会话未读、同步群消息阅读状态和定位消息序号

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'mark_group_msg_as_read', payload)

    # napcat_tool: napcat_mark_msg_as_read
    async def napcat_mark_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        user_id: int = None,
    ):
        """按消息 ID 标记消息为已读，适合清除指定消息未读、同步阅读状态和消息确认

Args:
    group_id(int): 可选，与user_id二选一。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    user_id(int): 可选，与user_id二选一。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'mark_msg_as_read', payload)

    async def napcat_mark_private_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
        group_id: int = None,
        message_id: int = None,
    ):
        """标记指定私聊消息为已读，适合清除好友会话未读、同步私聊阅读状态和消息确认

Args:
    user_id(int): 可选，用户QQ。默认使用当前消息发送者的用户 ID。
    group_id(int): 可选，群号。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'mark_private_msg_as_read', payload)

    # napcat_tool: napcat_move_group_file
    async def napcat_move_group_file_tool(
        self,
        event: AstrMessageEvent,
        current_parent_directory: str,
        file_id: str,
        target_parent_directory: str,
        group_id: int = None,
    ):
        """移动群文件到指定文件夹，适合整理群共享文件、迁移资料目录和调整群文件分类

Args:
    current_parent_directory(str): 必填，根目录填 /。
    file_id(str): 必填，文件ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    target_parent_directory(str): 必填，目标父目录。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if current_parent_directory is not None:
            payload['current_parent_directory'] = current_parent_directory
        if file_id is not None:
            payload['file_id'] = file_id
        payload['group_id'] = group_id
        if target_parent_directory is not None:
            payload['target_parent_directory'] = target_parent_directory
        return await self._call_napcat_api(event, 'move_group_file', payload)

    async def napcat_nc_get_packet_status_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取底层 Packet 服务状态，适合诊断协议连接、网络收发、底层服务和性能问题

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'nc_get_packet_status', payload)

    async def napcat_nc_get_rkey_tool(
        self,
        event: AstrMessageEvent,
    ):
        """通过 NapCat 底层接口获取 rkey，适合资源下载鉴权、图片语音文件链接和协议调试

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'nc_get_rkey', payload)

    # napcat_tool: napcat_nc_get_user_status
    async def napcat_nc_get_user_status_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
    ):
        """获取用户在线状态，适合查询好友或用户是否在线、客户端状态和可联系状态

Args:
    user_id(int): 可选，QQ号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'nc_get_user_status', payload)

    # napcat_tool: napcat_ocr_image
    async def napcat_ocr_image_tool(
        self,
        event: AstrMessageEvent,
        image: str,
    ):
        """识别图片文字，仅 Windows 可用，适合 OCR 提取截图、图片、聊天图片和表情包文本

Args:
    image(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, 'ocr_image', payload)

    # napcat_tool: napcat_qidian_get_account_info
    async def napcat_qidian_get_account_info_tool(
        self,
        event: AstrMessageEvent,
    ):
        """获取 QQ 企点账号信息，适合查询企业账号、企点资料、客服账号和商业身份信息

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'qidian_get_account_info', payload)

    # napcat_tool: napcat_receive_online_file
    async def napcat_receive_online_file_tool(
        self,
        event: AstrMessageEvent,
        element_id: str,
        msg_id: str,
        user_id: int = None,
    ):
        """接收在线文件传输，适合同意好友发送的在线文件、开始下载和保存传输文件

Args:
    element_id(str): 必填，元素 ID。
    msg_id(str): 必填，消息 ID。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if element_id is not None:
            payload['element_id'] = element_id
        if msg_id is not None:
            payload['msg_id'] = msg_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'receive_online_file', payload)

    # napcat_tool: napcat_refuse_online_file
    async def napcat_refuse_online_file_tool(
        self,
        event: AstrMessageEvent,
        element_id: str,
        msg_id: str,
        user_id: int = None,
    ):
        """拒绝在线文件传输，适合拒收好友文件、取消接收请求和处理不需要的传输文件

Args:
    element_id(str): 必填，元素 ID。
    msg_id(str): 必填，消息 ID。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if element_id is not None:
            payload['element_id'] = element_id
        if msg_id is not None:
            payload['msg_id'] = msg_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'refuse_online_file', payload)

    async def napcat_reload_event_filter_tool(
        self,
        event: AstrMessageEvent,
        file: str,
    ):
        """重载事件过滤器，适合刷新 NapCat 事件规则、过滤配置和消息事件处理策略

Args:
    file(str): 必填，事件过滤器文件。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        return await self._call_napcat_api(event, 'reload_event_filter', payload)

    # napcat_tool: napcat_rename_group_file
    async def napcat_rename_group_file_tool(
        self,
        event: AstrMessageEvent,
        current_parent_directory: str,
        file_id: str,
        new_name: str,
        group_id: int = None,
    ):
        """重命名群文件，适合修改群共享文件名称、整理资料标题和修正文件命名

Args:
    current_parent_directory(str): 必填，当前父目录。
    file_id(str): 必填，文件ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    new_name(str): 必填，新文件名。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if current_parent_directory is not None:
            payload['current_parent_directory'] = current_parent_directory
        if file_id is not None:
            payload['file_id'] = file_id
        payload['group_id'] = group_id
        if new_name is not None:
            payload['new_name'] = new_name
        return await self._call_napcat_api(event, 'rename_group_file', payload)

    # napcat_tool: napcat_send_ark_share
    async def napcat_send_ark_share_tool(
        self,
        event: AstrMessageEvent,
        phone_number: str,
        group_id: int = None,
        user_id: int = None,
        send_group_id: int = None,
        send_user_id: int = None,
    ):
        """获取用户推荐 Ark 卡片并自动发送，适合分享联系人名片、好友推荐和用户邀请卡片

Args:
    phone_number(str): 必填，手机号。
    group_id(int): 可选，群号。
    user_id(int): 可选，QQ号。
    send_group_id(int): 可选，要发送到的群号。和 send_user_id 都不填时默认发送到当前会话。
    send_user_id(int): 可选，要发送到的用户 QQ。和 send_group_id 都不填时默认发送到当前会话。

Returns:
    str: 返回 Ark 获取结果和自动发送结果的 JSON 字符串。"""
        payload: dict = {}
        if phone_number is not None:
            payload['phone_number'] = phone_number
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_ark_share_and_send(
            event, 'send_ark_share', payload, send_group_id, send_user_id
        )

    # napcat_tool: napcat_send_flash_msg
    async def napcat_send_flash_msg_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
        group_id: int = None,
        user_id: int = None,
    ):
        """发送闪传消息，适合发送大文件、文件集、快速传输资源和临时分享内容

Args:
    fileset_id(str): 必填，文件集 ID。
    group_id(int): 可选，群号。
    user_id(int): 可选，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_flash_msg', payload)

    # napcat_tool: napcat_send_forward_msg
    async def napcat_send_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str = None,
        messages: list = None,
        message_id: int = None,
        message_ids: list = None,
        group_id: int = None,
        user_id: int = None,
        auto_escape: str = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """统一发送合并转发和单条转发，适合把历史消息 message_id 自动组成 node 节点后发到群聊或私聊

Args:
    message(str): 可选，兼容字段；发送合并转发时通常传空字符串或简短标题，核心内容放在 messages。
    messages(list): 可选，合并转发节点列表。可直接传 `[{"type":"node","data":{"id": message_id}}]`；如果已传 message_id 或 message_ids，可省略。
    message_id(int): 可选，单条要转发的消息 ID。省略 messages 和 message_ids 时，默认优先使用被回复消息 ID，再回退当前消息 ID。
    message_ids(list): 可选，多条要打包转发的消息 ID 列表；工具会自动转为 node 节点列表。
    auto_escape(str): 可选，是否作为纯文本发送。
    group_id(int): 可选，目标群号。默认在群聊中使用当前群号。
    message_type(str): 可选，目标类型，支持 `group` 或 `private`；不填时优先按 group_id/user_id 和当前会话判断。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，目标用户 QQ。默认在私聊中使用当前消息发送者 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        normalized_type = (message_type or "").lower()
        if messages is None:
            ids = []
            if message_ids:
                ids.extend(message_ids)
            elif message_id is not None:
                ids.append(message_id)
            else:
                default_message_id = self._get_default_message_id(event)
                if default_message_id:
                    ids.append(default_message_id)
            messages = [
                {"type": "node", "data": {"id": int(item) if str(item).isdigit() else item}}
                for item in ids
            ]

        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if normalized_type in {"group", "guild"} or group_id is not None:
            payload["group_id"] = group_id
            return await self._call_napcat_api(event, "send_group_forward_msg", payload)
        if normalized_type in {"private", "friend"} or user_id is not None:
            payload["user_id"] = user_id
            return await self._call_napcat_api(event, "send_private_forward_msg", payload)
        if self._get_current_group_id_or_none(event) is not None:
            payload["group_id"] = group_id
            return await self._call_napcat_api(event, "send_group_forward_msg", payload)
        payload["user_id"] = user_id
        return await self._call_napcat_api(event, "send_private_forward_msg", payload)

    # napcat_tool: napcat_send_group_ai_record
    async def napcat_send_group_ai_record_tool(
        self,
        event: AstrMessageEvent,
        character: str,
        text: str,
        group_id: int = None,
    ):
        """发送 AI 生成语音到群聊，适合群内 TTS、AI 声线配音、角色语音和文字转语音

Args:
    character(str): 必填，character_id。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    text(str): 必填，语音文本内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if character is not None:
            payload['character'] = character
        payload['group_id'] = group_id
        if text is not None:
            payload['text'] = text
        return await self._call_napcat_api(event, 'send_group_ai_record', payload)

    # napcat_tool: napcat_send_group_ark_share
    async def napcat_send_group_ark_share_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        send_group_id: int = None,
        send_user_id: int = None,
    ):
        """获取群分享 Ark 卡片并自动发送，适合分享群名片、群邀请、群资料和入群卡片

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    send_group_id(int): 可选，要发送到的群号。和 send_user_id 都不填时默认发送到当前会话。
    send_user_id(int): 可选，要发送到的用户 QQ。和 send_group_id 都不填时默认发送到当前会话。

Returns:
    str: 返回 Ark 获取结果和自动发送结果的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_ark_share_and_send(
            event, 'send_group_ark_share', payload, send_group_id, send_user_id
        )

    async def napcat_send_group_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        messages: list,
        group_id: int = None,
        user_id: int = None,
        auto_escape: str = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """发送群合并转发聊天记录，适合把历史消息 message_id 转成 node 节点后发到群聊

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message(str): 必填，兼容字段；发送群合并转发时通常传空字符串或简短标题，核心内容放在 messages。
    messages(list): 必填，合并转发节点列表。转发群历史消息时先调用 `napcat_get_group_msg_history` 获取 message_id，再传 `[{"type":"node","data":{"id": message_id}}]`；多条消息就传多个 node。
    auto_escape(str): 可选，是否作为纯文本发送。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_group_forward_msg', payload)

    async def napcat_send_group_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        group_id: int = None,
        user_id: int = None,
        auto_escape: bool = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """发送群消息，适合向群聊发送文本、图片、语音、表情、JSON、回复和消息段

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message(str): 必填，要发送的内容。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_group_msg', payload)

    # napcat_tool: napcat_send_group_notice
    async def napcat_send_group_notice_tool(
        self,
        event: AstrMessageEvent,
        confirm_required: str,
        content: str,
        is_show_edit_card: str,
        pinned: str,
        tip_window_type: str,
        type: str,
        group_id: int = None,
        image: str = None,
    ):
        """发送群公告，适合发布群通知、置顶公告、重要提醒和群管理消息

Args:
    confirm_required(str): 必填，是否需要确认 (0/1)。
    content(str): 必填，公告内容。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    is_show_edit_card(str): 必填，是否显示修改群名片引导 (0/1)。
    pinned(str): 必填，是否置顶 (0/1)。
    tip_window_type(str): 必填，弹窗类型 (默认为 0)。
    type(str): 必填，类型 (默认为 1)。
    image(str): 可选，公告图片路径或 URL。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if confirm_required is not None:
            payload['confirm_required'] = confirm_required
        if content is not None:
            payload['content'] = content
        payload['group_id'] = group_id
        if is_show_edit_card is not None:
            payload['is_show_edit_card'] = is_show_edit_card
        if pinned is not None:
            payload['pinned'] = pinned
        if tip_window_type is not None:
            payload['tip_window_type'] = tip_window_type
        if type is not None:
            payload['type'] = type
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, '_send_group_notice', payload)

    # napcat_tool: napcat_send_group_sign
    async def napcat_send_group_sign_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """执行群打卡，适合群签到、每日打卡、活跃任务和群互动签到

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'send_group_sign', payload)

    # napcat_tool: napcat_send_guild_channel_msg
    async def napcat_send_guild_channel_msg_tool(
        self,
        event: AstrMessageEvent,
        channel_id: str = None,
        guild_id: str = None,
        message: str = None,
    ):
        """发送频道子频道消息，适合向 guild 子频道发送文本、图片、消息段和频道通知

Args:
    channel_id(str): 可选，子频道ID。
    guild_id(str): 可选，频道ID。
    message(str): 可选，消息, 与原有消息类型相同。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if channel_id is not None:
            payload['channel_id'] = channel_id
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if message is not None:
            payload['message'] = message
        return await self._call_napcat_api(event, 'send_guild_channel_msg', payload)

    # napcat_tool: napcat_send_like
    async def napcat_send_like_tool(
        self,
        event: AstrMessageEvent,
        times: int = 1,
        user_id: int = None,
    ):
        """给用户资料卡点赞，适合对 QQ 用户点赞、名片点赞、主页互动和好友点赞任务

Args:
    times(int): 可选，赞的次数，每个好友每天最多 10 次。默认值为 1。
    user_id(int): 可选，对方 QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if times is not None:
            payload['times'] = times
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_like', payload)

    # napcat_tool: napcat_send_msg
    async def napcat_send_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        message_type: str,
        group_id: int = None,
        user_id: int = None,
        auto_escape: bool = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """发送消息到群聊或私聊，适合自动按目标类型发送文本、图片、语音、表情、JSON 和消息段

Args:
    group_id(int): 可选，群号 ( 消息类型为 `group` 时需要 )。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message(str): 必填，要发送的内容。
    message_type(str): 必填，消息类型, 支持 `private`、`group` , 分别对应私聊、群组, 如不传入, 则根据传入的 `*_id` 参数判断。
    user_id(int): 可选，对方 QQ 号 ( 消息类型为 `private` 时需要 )。默认使用当前消息发送者的用户 ID。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if message_type is not None:
            payload['message_type'] = message_type
        payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_msg', payload)

    # napcat_tool: napcat_send_online_file
    async def napcat_send_online_file_tool(
        self,
        event: AstrMessageEvent,
        file_path: str,
        user_id: int = None,
        file_name: str = None,
    ):
        """发送在线文件给用户，适合向好友传输本地文件、临时文件和在线文件任务

Args:
    file_path(str): 必填，本地文件路径。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。
    file_name(str): 可选，文件名 (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_path is not None:
            payload['file_path'] = file_path
        payload['user_id'] = user_id
        if file_name is not None:
            payload['file_name'] = file_name
        return await self._call_napcat_api(event, 'send_online_file', payload)

    # napcat_tool: napcat_send_online_folder
    async def napcat_send_online_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_path: str,
        user_id: int = None,
        folder_name: str = None,
    ):
        """发送在线文件夹给用户，适合批量传输目录、文件夹资源和多文件在线传输

Args:
    folder_path(str): 必填，本地文件夹路径。
    user_id(int): 可选，用户 QQ。默认使用当前消息发送者的用户 ID。
    folder_name(str): 可选，文件夹名称 (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_path is not None:
            payload['folder_path'] = folder_path
        payload['user_id'] = user_id
        if folder_name is not None:
            payload['folder_name'] = folder_name
        return await self._call_napcat_api(event, 'send_online_folder', payload)

    async def napcat_send_packet_tool(
        self,
        event: AstrMessageEvent,
        cmd: str,
        data: str,
        rsp: str,
    ):
        """发送底层原始数据包，适合协议调试、Packet 测试、低层接口实验和高级诊断

Args:
    cmd(str): 必填，命令字。
    data(str): 必填，十六进制数据。
    rsp(str): 必填，是否等待响应。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if cmd is not None:
            payload['cmd'] = cmd
        if data is not None:
            payload['data'] = data
        if rsp is not None:
            payload['rsp'] = rsp
        return await self._call_napcat_api(event, 'send_packet', payload)

    # napcat_tool: napcat_send_poke
    async def napcat_send_poke_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None,
        group_id: int = None,
        target_id: int = None,
    ):
        """发送戳一戳到群聊或私聊，适合提醒用户、拍一拍、poke 和轻互动动作

Args:
    user_id(int): 可选，要戳的 QQ 号。默认使用当前消息发送者的用户 ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；私聊中不传则按私聊戳一戳处理。
    target_id(int): 可选，兼容别名，等同于 user_id；当 user_id 未提供时会作为要戳的 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is None and target_id is not None:
            user_id = target_id
        payload['user_id'] = user_id
        if group_id is None:
            group_id = self._get_current_group_id_or_none(event)
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'send_poke', payload)

    async def napcat_send_private_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        messages: list,
        user_id: int = None,
        group_id: int = None,
        auto_escape: str = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """发送私聊合并转发聊天记录，适合把历史消息 message_id 转成 node 节点后发给好友

Args:
    message(str): 必填，兼容字段；发送私聊合并转发时通常传空字符串或简短标题，核心内容放在 messages。
    messages(list): 必填，合并转发节点列表。转发历史消息时先调用历史消息工具获取 message_id，再传 `[{"type":"node","data":{"id": message_id}}]`；多条消息就传多个 node。
    user_id(int): 可选，好友QQ号。默认使用当前消息发送者的用户 ID。
    auto_escape(str): 可选，是否作为纯文本发送。
    group_id(int): 可选，群号。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if group_id is not None:
            payload['group_id'] = group_id
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_private_forward_msg', payload)

    async def napcat_send_private_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        group_id: int = None,
        user_id: int = None,
        auto_escape: bool = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
    ):
        """发送私聊消息，适合向指定用户发送文本、图片、语音、表情、JSON、回复和消息段

Args:
    group_id(int): 可选，主动发起临时会话时的来源群号(可选, 机器人本身必须是管理员/群主)。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message(str): 必填，要发送的内容。
    user_id(int): 可选，对方 QQ 号。默认使用当前消息发送者的用户 ID。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_private_msg', payload)

    # napcat_tool: napcat_set_diy_online_status
    async def napcat_set_diy_online_status_tool(
        self,
        event: AstrMessageEvent,
        face_id: str,
        face_type: str,
        wording: str,
    ):
        """设置自定义在线状态，适合修改在线、忙碌、离开、隐身、设备状态和扩展状态展示

Args:
    face_id(str): 必填，图标ID。
    face_type(str): 必填，图标类型。
    wording(str): 必填，状态文字内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if face_id is not None:
            payload['face_id'] = face_id
        if face_type is not None:
            payload['face_type'] = face_type
        if wording is not None:
            payload['wording'] = wording
        return await self._call_napcat_api(event, 'set_diy_online_status', payload)

    # napcat_tool: napcat_set_doubt_friends_add_request
    async def napcat_set_doubt_friends_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str,
    ):
        """处理可疑好友申请，适合同意、拒绝、忽略风控好友请求和异常加好友通知

Args:
    approve(bool): 必填，是否同意 (强制为 true)。
    flag(str): 必填，请求 flag。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        return await self._call_napcat_api(event, 'set_doubt_friends_add_request', payload)

    # napcat_tool: napcat_set_essence_msg
    async def napcat_set_essence_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int = None,
    ):
        """设置群精华消息，适合把重要群消息加入精华、收藏公告内容和标记重点讨论

Args:
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'set_essence_msg', payload)

    # napcat_tool: napcat_set_friend_add_request
    async def napcat_set_friend_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str,
        remark: str,
    ):
        """处理加好友请求，适合同意好友申请、拒绝好友申请和设置好友备注

Args:
    approve(bool): 必填，是否同意请求 默认值: `true`。
    flag(str): 必填，加好友请求的 flag（需从上报的数据中获得）。
    remark(str): 必填，添加后的好友备注（仅在同意时有效） 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        if remark is not None:
            payload['remark'] = remark
        return await self._call_napcat_api(event, 'set_friend_add_request', payload)

    # napcat_tool: napcat_set_friend_remark
    async def napcat_set_friend_remark_tool(
        self,
        event: AstrMessageEvent,
        remark: str,
        user_id: int = None,
    ):
        """设置好友备注，适合修改联系人备注、好友名称、别名和通讯录显示名

Args:
    remark(str): 必填，备注内容。
    user_id(int): 可选，对方 QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if remark is not None:
            payload['remark'] = remark
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_friend_remark', payload)

    # napcat_tool: napcat_set_group_add_option
    async def napcat_set_group_add_option_tool(
        self,
        event: AstrMessageEvent,
        add_type: int,
        group_id: int = None,
        group_answer: str = None,
        group_question: str = None,
    ):
        """设置群加群验证选项，适合配置入群方式、加群审批、问题验证和群申请规则

Args:
    add_type(int): 必填，加群方式。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    group_answer(str): 可选，加群答案。
    group_question(str): 可选，加群问题。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if add_type is not None:
            payload['add_type'] = add_type
        payload['group_id'] = group_id
        if group_answer is not None:
            payload['group_answer'] = group_answer
        if group_question is not None:
            payload['group_question'] = group_question
        return await self._call_napcat_api(event, 'set_group_add_option', payload)

    # napcat_tool: napcat_set_group_add_request
    async def napcat_set_group_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str,
        count: int = None,
        reason: str = None,
    ):
        """处理加群请求或邀请，适合同意入群申请、拒绝加群申请和审批群邀请

Args:
    approve(bool): 必填，是否同意请求／邀请 默认值: `true`。
    flag(str): 必填，加群请求的 flag（需从上报的数据中获得）。
    count(int): 可选，搜索通知数量。
    reason(str): 可选，拒绝理由（仅在拒绝时有效） 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        if count is not None:
            payload['count'] = count
        if reason is not None:
            payload['reason'] = reason
        return await self._call_napcat_api(event, 'set_group_add_request', payload)

    # napcat_tool: napcat_set_group_admin
    async def napcat_set_group_admin_tool(
        self,
        event: AstrMessageEvent,
        enable: bool,
        group_id: int = None,
        user_id: int = None,
    ):
        """设置群管理员，适合授予或取消群管理权限、调整管理员和群管身份

Args:
    enable(bool): 必填，true 为设置, false 为取消 默认值: `true`。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，要设置管理员的 QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if enable is not None:
            payload['enable'] = enable
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_group_admin', payload)

    # napcat_tool: napcat_set_group_album_media_like
    async def napcat_set_group_album_media_like_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        id: str,
        lloc: str,
        set: bool,
        group_id: int = None,
    ):
        """点赞群相册媒体，适合给群相册图片、视频、相册动态和媒体资源点赞

Args:
    album_id(str): 必填，相册ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    id(str): 必填，点赞ID。
    lloc(str): 必填，媒体ID (lloc)。
    set(bool): 必填，是否点赞。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        payload['group_id'] = group_id
        if id is not None:
            payload['id'] = id
        if lloc is not None:
            payload['lloc'] = lloc
        if set is not None:
            payload['set'] = set
        return await self._call_napcat_api(event, 'set_group_album_media_like', payload)

    # napcat_tool: napcat_set_group_anonymous
    async def napcat_set_group_anonymous_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        enable: bool = None,
    ):
        """设置群匿名聊天开关，适合启用或关闭群匿名、匿名发言和群匿名功能

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    enable(bool): 可选，是否允许匿名聊天 默认值: `true`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if enable is not None:
            payload['enable'] = enable
        return await self._call_napcat_api(event, 'set_group_anonymous', payload)

    # napcat_tool: napcat_set_group_anonymous_ban
    async def napcat_set_group_anonymous_ban_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        anonymous: dict = None,
        anonymous_flag: str = None,
        duration: int = None,
        flag: str = None,
    ):
        """禁言群匿名用户，适合按匿名标识限制匿名发言、处理匿名违规和群管理禁言

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    anonymous(dict): 可选，可选, 要禁言的匿名用户对象（群消息上报的 `anonymous` 字段）。
    anonymous_flag(str): 可选，可选, 要禁言的匿名用户的 flag（需从群消息上报的数据中获得）。
    duration(int): 可选，禁言时长, 单位秒, 无法取消匿名用户禁言 默认值: `30 * 60`。
    flag(str): 可选，可选, 要禁言的匿名用户的 flag（需从群消息上报的数据中获得）。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if anonymous is not None:
            payload['anonymous'] = anonymous
        if anonymous_flag is not None:
            payload['anonymous_flag'] = anonymous_flag
        if duration is not None:
            payload['duration'] = duration
        if flag is not None:
            payload['flag'] = flag
        return await self._call_napcat_api(event, 'set_group_anonymous_ban', payload)

    # napcat_tool: napcat_set_group_ban
    async def napcat_set_group_ban_tool(
        self,
        event: AstrMessageEvent,
        duration: int,
        group_id: int = None,
        user_id: int = None,
    ):
        """禁言群成员，适合设置指定成员禁言时长、解除禁言和群管理处罚

Args:
    duration(int): 必填，禁言时长, 单位秒, 0 表示取消禁言 默认值: `30 * 60`。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，要禁言的 QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if duration is not None:
            payload['duration'] = duration
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_group_ban', payload)

    # napcat_tool: napcat_set_group_card
    async def napcat_set_group_card_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        user_id: int = None,
        card: str = None,
    ):
        """设置群成员名片，适合修改指定成员群昵称、群名片和群内显示名称

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，要设置的 QQ 号。默认使用当前消息发送者的用户 ID。
    card(str): 可选，群名片内容, 不填或空字符串表示删除群名片 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        if card is not None:
            payload['card'] = card
        return await self._call_napcat_api(event, 'set_group_card', payload)

    # napcat_tool: napcat_set_group_kick
    async def napcat_set_group_kick_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        user_id: int = None,
        reject_add_request: bool = None,
    ):
        """踢出群成员，适合将指定用户移出群聊、拒绝再次加群和群管理清退

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，要踢的 QQ 号。默认使用当前消息发送者的用户 ID。
    reject_add_request(bool): 可选，拒绝此人的加群请求 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        if reject_add_request is not None:
            payload['reject_add_request'] = reject_add_request
        return await self._call_napcat_api(event, 'set_group_kick', payload)

    # napcat_tool: napcat_set_group_kick_members
    async def napcat_set_group_kick_members_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        user_id: int = None,
        reject_add_request: bool = None,
    ):
        """批量踢出群成员，适合一次移除多个用户、群清理、批量群管理和成员清退

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    user_id(int): 可选，QQ号列表。默认使用当前消息发送者的用户 ID。
    reject_add_request(bool): 可选，是否拒绝加群请求。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        payload['user_id'] = user_id
        if reject_add_request is not None:
            payload['reject_add_request'] = reject_add_request
        return await self._call_napcat_api(event, 'set_group_kick_members', payload)

    # napcat_tool: napcat_set_group_leave
    async def napcat_set_group_leave_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        is_dismiss: bool = None,
    ):
        """退出或解散群聊，适合机器人退群、群主解散群和结束群会话

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    is_dismiss(bool): 可选，是否解散, 如果登录号是群主, 则仅在此项为 true 时能够解散 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if is_dismiss is not None:
            payload['is_dismiss'] = is_dismiss
        return await self._call_napcat_api(event, 'set_group_leave', payload)

    # napcat_tool: napcat_set_group_name
    async def napcat_set_group_name_tool(
        self,
        event: AstrMessageEvent,
        group_name: str,
        group_id: int = None,
    ):
        """设置群名称，适合修改群名、群标题、群资料名称和群聊显示名称

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    group_name(str): 必填，群名称。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if group_name is not None:
            payload['group_name'] = group_name
        return await self._call_napcat_api(event, 'set_group_name', payload)

    # napcat_tool: napcat_set_group_portrait
    async def napcat_set_group_portrait_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        group_id: int = None,
        cache: int = None,
    ):
        """设置群头像，适合修改群聊头像、群图片、群资料封面和群标识图片

Args:
    file(str): 必填，头像文件路径或 URL。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    cache(int): 可选，表示是否使用已缓存的文件。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        payload['group_id'] = group_id
        if cache is not None:
            payload['cache'] = cache
        return await self._call_napcat_api(event, 'set_group_portrait', payload)

    # napcat_tool: napcat_set_group_remark
    async def napcat_set_group_remark_tool(
        self,
        event: AstrMessageEvent,
        remark: str,
        group_id: int = None,
    ):
        """设置群备注，适合修改本地群备注、群别名和群列表显示名称

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    remark(str): 必填，备注。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if remark is not None:
            payload['remark'] = remark
        return await self._call_napcat_api(event, 'set_group_remark', payload)

    # napcat_tool: napcat_set_group_robot_add_option
    async def napcat_set_group_robot_add_option_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        robot_member_examine: int = None,
        robot_member_switch: int = None,
    ):
        """设置群机器人加群选项，适合配置机器人入群审批、机器人邀请和自动加群规则

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    robot_member_examine(int): 可选，机器人成员审核。
    robot_member_switch(int): 可选，机器人成员开关。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if robot_member_examine is not None:
            payload['robot_member_examine'] = robot_member_examine
        if robot_member_switch is not None:
            payload['robot_member_switch'] = robot_member_switch
        return await self._call_napcat_api(event, 'set_group_robot_add_option', payload)

    # napcat_tool: napcat_set_group_search
    async def napcat_set_group_search_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        no_code_finger_open: int = None,
        no_finger_open: int = None,
    ):
        """设置群搜索可见性，适合允许或禁止被搜索、群公开检索和群发现入口配置

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    no_code_finger_open(int): 可选，未知。
    no_finger_open(int): 可选，未知。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if no_code_finger_open is not None:
            payload['no_code_finger_open'] = no_code_finger_open
        if no_finger_open is not None:
            payload['no_finger_open'] = no_finger_open
        return await self._call_napcat_api(event, 'set_group_search', payload)

    # napcat_tool: napcat_set_group_sign
    async def napcat_set_group_sign_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
    ):
        """设置或执行群签到打卡，适合群每日打卡、活跃签到和群互动任务

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'set_group_sign', payload)

    # napcat_tool: napcat_set_group_special_title
    async def napcat_set_group_special_title_tool(
        self,
        event: AstrMessageEvent,
        special_title: str,
        group_id: int = None,
        user_id: int = None,
        duration: int = None,
    ):
        """设置群成员专属头衔，适合修改群头衔、特殊称号、荣誉称号和成员标签

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    special_title(str): 必填，专属头衔, 不填或空字符串表示删除专属头衔 默认值: 空。
    user_id(int): 可选，要设置的 QQ 号。默认使用当前消息发送者的用户 ID。
    duration(int): 可选，专属头衔有效期, 单位秒, -1 表示永久, 不过此项似乎没有效果, 可能是只有某些特殊的时间长度有效, 有待测试 默认值: `-1`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        if special_title is not None:
            payload['special_title'] = special_title
        payload['user_id'] = user_id
        if duration is not None:
            payload['duration'] = duration
        return await self._call_napcat_api(event, 'set_group_special_title', payload)

    # napcat_tool: napcat_set_group_todo
    async def napcat_set_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        message_seq: int = None,
    ):
        """设置群待办，适合把消息设为群任务、群提醒、待办事项和需要成员确认的消息

Args:
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        payload['group_id'] = group_id
        payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'set_group_todo', payload)

    # napcat_tool: napcat_set_group_whole_ban
    async def napcat_set_group_whole_ban_tool(
        self,
        event: AstrMessageEvent,
        enable: bool,
        group_id: int = None,
    ):
        """设置群全体禁言，适合开启或关闭全员禁言、群静默和群管理管控

Args:
    enable(bool): 必填，是否开启全员禁言 默认值: `true`。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if enable is not None:
            payload['enable'] = enable
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'set_group_whole_ban', payload)

    # napcat_tool: napcat_set_guild_member_role
    async def napcat_set_guild_member_role_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str,
        role_id: str,
        set: bool = None,
        users: str = None,
    ):
        """设置频道成员角色，适合给用户添加或移除频道身份组、权限角色和成员分组

Args:
    guild_id(str): 必填，频道ID。
    role_id(str): 必填，频道ID。
    set(bool): 可选，是否设置(默认假，取消) 默认值: false。
    users(str): 可选，- 默认值: array。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if role_id is not None:
            payload['role_id'] = role_id
        if set is not None:
            payload['set'] = set
        if users is not None:
            payload['users'] = users
        return await self._call_napcat_api(event, 'set_guild_member_role', payload)

    # napcat_tool: napcat_set_input_status
    async def napcat_set_input_status_tool(
        self,
        event: AstrMessageEvent,
        event_type: int,
        user_id: int = None,
    ):
        """设置输入状态，适合展示正在输入、取消输入提示和私聊输入状态同步

Args:
    event_type(int): 必填，事件类型。
    user_id(int): 可选，QQ号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if event_type is not None:
            payload['event_type'] = event_type
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_input_status', payload)

    # napcat_tool: napcat_set_model_show
    async def napcat_set_model_show_tool(
        self,
        event: AstrMessageEvent,
        model: str = None,
        model_show: str = None,
    ):
        """设置在线机型展示，适合修改在线设备名称、客户端机型和资料卡设备显示

Args:
    model(str): 可选，机型名称。
    model_show(str): 可选，-。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if model is not None:
            payload['model'] = model
        if model_show is not None:
            payload['model_show'] = model_show
        return await self._call_napcat_api(event, '_set_model_show', payload)

    # napcat_tool: napcat_set_msg_emoji_like
    async def napcat_set_msg_emoji_like_tool(
        self,
        event: AstrMessageEvent,
        emoji_id: int,
        set: bool,
        message_id: int = None,
    ):
        """设置消息表情回应，适合给消息添加或取消 Emoji 点赞、表情反应和互动回应

Args:
    emoji_id(int): 必填，表情ID。
    message_id(int): 可选，消息ID。默认优先使用被回复消息 ID；未回复或解析失败时使用当前消息 ID。
    set(bool): 必填，是否设置。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if emoji_id is not None:
            payload['emoji_id'] = emoji_id
        payload['message_id'] = message_id
        if set is not None:
            payload['set'] = set
        return await self._call_napcat_api(event, 'set_msg_emoji_like', payload)

    # napcat_tool: napcat_set_online_status
    async def napcat_set_online_status_tool(
        self,
        event: AstrMessageEvent,
        battery_status: str,
        batteryStatus: int,
        ext_status: str,
        extStatus: int,
        status: int,
    ):
        """设置 QQ 在线状态，适合切换在线、离开、忙碌、隐身、Q我吧、电量和扩展状态

Args:
    battery_status(str): 必填，电量状态。
    batteryStatus(int): 必填，电量。
    ext_status(str): 必填，扩展状态。
    extStatus(int): 必填，详情看顶部。
    status(int): 必填，详情看顶部。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if battery_status is not None:
            payload['battery_status'] = battery_status
        if batteryStatus is not None:
            payload['batteryStatus'] = batteryStatus
        if ext_status is not None:
            payload['ext_status'] = ext_status
        if extStatus is not None:
            payload['extStatus'] = extStatus
        if status is not None:
            payload['status'] = status
        return await self._call_napcat_api(event, 'set_online_status', payload)

    # napcat_tool: napcat_set_qq_avatar
    async def napcat_set_qq_avatar_tool(
        self,
        event: AstrMessageEvent,
        file: str,
    ):
        """修改当前账号 QQ 头像，适合上传新头像、更新机器人头像和设置个人资料图片

Args:
    file(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        return await self._call_napcat_api(event, 'set_qq_avatar', payload)

    # napcat_tool: napcat_set_qq_profile
    async def napcat_set_qq_profile_tool(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str = None,
        sex: str = None,
    ):
        """修改当前账号资料，适合更新 QQ 昵称、签名、性别、生日、邮箱和个人资料字段

Args:
    nickname(str): 必填，昵称。
    personal_note(str): 可选，个性签名。
    sex(str): 可选，性别 (0: 未知, 1: 男, 2: 女)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if nickname is not None:
            payload['nickname'] = nickname
        if personal_note is not None:
            payload['personal_note'] = personal_note
        if sex is not None:
            payload['sex'] = sex
        return await self._call_napcat_api(event, 'set_qq_profile', payload)

    # napcat_tool: napcat_set_restart
    async def napcat_set_restart_tool(
        self,
        event: AstrMessageEvent,
        delay: int = None,
    ):
        """重启 NapCat 服务，适合远程重启、应用配置、恢复异常和重新启动机器人服务

Args:
    delay(int): 可选，要延迟的毫秒数, 如果默认情况下无法重启, 可以尝试设置延迟为 2000 左右 默认值: `0`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if delay is not None:
            payload['delay'] = delay
        return await self._call_napcat_api(event, 'set_restart', payload)

    # napcat_tool: napcat_set_self_longnick
    async def napcat_set_self_longnick_tool(
        self,
        event: AstrMessageEvent,
        longNick: str,
    ):
        """修改当前账号个性签名，适合设置 longnick、个人签名、状态文案和资料卡签名

Args:
    longNick(str): 必填，签名内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if longNick is not None:
            payload['longNick'] = longNick
        return await self._call_napcat_api(event, 'set_self_longnick', payload)

    async def napcat_test_download_stream_tool(
        self,
        event: AstrMessageEvent,
        error: bool = None,
    ):
        """测试流式下载，适合验证下载流、网络资源读取、文件流稳定性和调试下载接口

Args:
    error(bool): 可选，是否触发测试错误。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if error is not None:
            payload['error'] = error
        return await self._call_napcat_api(event, 'test_download_stream', payload)

    # napcat_tool: napcat_trans_group_file
    async def napcat_trans_group_file_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int = None,
    ):
        """转存或传输群文件，适合在群文件系统内复制、转移、保存和处理共享文件资源

Args:
    file_id(str): 必填，文件ID。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'trans_group_file', payload)

    # disabled napcat_tool: napcat_translate_en2zh
    # async def napcat_translate_en2zh_tool(
    #     self,
    #     event: AstrMessageEvent,
    #     words: list,
    # ):
    #     """将英文单词列表翻译为中文
    #
    # Args:
    #     words(list): 必填，待翻译单词列表。
    #
    # Returns:
    #     str: 返回 API 响应的 JSON 字符串。"""
    #     payload: dict = {}
    #     if words is not None:
    #         if isinstance(words, str):
    #             words = [words]
    #         payload['words'] = words
    #     return await self._call_napcat_api(event, 'translate_en2zh', payload)

    async def napcat_unknown_tool(
        self,
        event: AstrMessageEvent,
    ):
        """调用未归类 NapCat 接口，适合临时兼容未知动作、实验接口和调试未命名能力

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'unknown', payload)

    # napcat_tool: napcat_update_guild_role
    async def napcat_update_guild_role_tool(
        self,
        event: AstrMessageEvent,
        color: str,
        guild_id: str,
        name: str,
        role_id: str,
        independent: bool = None,
    ):
        """修改频道角色信息，适合更新频道身份组名称、颜色、权限配置和角色排序

Args:
    color(str): 必填，颜色(示例:4294927682)。
    guild_id(str): 必填，频道ID。
    name(str): 必填，角色名。
    role_id(str): 必填，角色ID。
    independent(bool): 可选，未知 默认值: false。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if color is not None:
            payload['color'] = color
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if name is not None:
            payload['name'] = name
        if role_id is not None:
            payload['role_id'] = role_id
        if independent is not None:
            payload['independent'] = independent
        return await self._call_napcat_api(event, 'update_guild_role', payload)

    # napcat_tool: napcat_upload_file_stream
    async def napcat_upload_file_stream_tool(
        self,
        event: AstrMessageEvent,
        file_retention: int,
        stream_id: str,
        chunk_data: str = None,
        chunk_index: int = None,
        expected_sha256: str = None,
        file_size: int = None,
        filename: str = None,
        is_complete: bool = None,
        reset: bool = None,
        total_chunks: int = None,
        verify_only: bool = None,
    ):
        """流式上传文件数据，适合上传本地文件、网络文件、二进制流和后续发送素材

Args:
    file_retention(int): 必填，默认5分钟回收 不设置或0为不回收。
    stream_id(str): 必填，流 ID。
    chunk_data(str): 可选，分块数据 (Base64)。
    chunk_index(int): 可选，分块索引。
    expected_sha256(str): 可选，期望的 SHA256。
    file_size(int): 可选，文件总大小。
    filename(str): 可选，文件名。
    is_complete(bool): 可选，是否完成。
    reset(bool): 可选，是否重置。
    total_chunks(int): 可选，总分块数。
    verify_only(bool): 可选，是否仅验证。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_retention is not None:
            payload['file_retention'] = file_retention
        if stream_id is not None:
            payload['stream_id'] = stream_id
        if chunk_data is not None:
            payload['chunk_data'] = chunk_data
        if chunk_index is not None:
            payload['chunk_index'] = chunk_index
        if expected_sha256 is not None:
            payload['expected_sha256'] = expected_sha256
        if file_size is not None:
            payload['file_size'] = file_size
        if filename is not None:
            payload['filename'] = filename
        if is_complete is not None:
            payload['is_complete'] = is_complete
        if reset is not None:
            payload['reset'] = reset
        if total_chunks is not None:
            payload['total_chunks'] = total_chunks
        if verify_only is not None:
            payload['verify_only'] = verify_only
        return await self._call_napcat_api(event, 'upload_file_stream', payload)

    # napcat_tool: napcat_upload_group_file
    async def napcat_upload_group_file_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        name: str,
        upload_file: bool,
        group_id: int = None,
        folder: str = None,
        folder_id: str = None,
    ):
        """上传文件到群文件，适合把本地路径、URL 或资源文件上传到群共享文件系统

Args:
    file(str): 必填，资源路径或URL。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。
    name(str): 必填，储存名称。
    upload_file(bool): 必填，是否执行上传。
    folder(str): 可选，文件夹ID（二选一）。
    folder_id(str): 可选，父目录 ID (兼容性字段)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        payload['group_id'] = group_id
        if name is not None:
            payload['name'] = name
        if upload_file is not None:
            payload['upload_file'] = upload_file
        if folder is not None:
            payload['folder'] = folder
        if folder_id is not None:
            payload['folder_id'] = folder_id
        return await self._call_napcat_api(event, 'upload_group_file', payload)

    # napcat_tool: napcat_upload_image_to_qun_album
    async def napcat_upload_image_to_qun_album_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        album_name: str,
        file: str = None,
        group_id: int = None,
    ):
        """上传图片到群相册，适合把回复图片、当前图片、URL 或本地图片保存到指定群相册；调用前通常需要先用 napcat_get_qun_album_list 获取相册 ID

Args:
    album_id(str): 必填，相册ID。
    album_name(str): 必填，相册名称。需要先调用 napcat_get_qun_album_list 获取准确名称。
    file(str): 可选，图片路径、URL或Base64。默认优先使用被回复消息里的第一张图片；没有回复图片时使用当前消息里的第一张图片。
    group_id(int): 可选，群号。默认使用当前群聊的群号；如果当前是私聊且未提供群号，会返回可读提示。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if album_name is not None:
            payload['album_name'] = album_name
        payload['file'] = file
        payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'upload_image_to_qun_album', payload)

    # napcat_tool: napcat_upload_private_file
    async def napcat_upload_private_file_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        name: str,
        upload_file: bool,
        user_id: int = None,
    ):
        """上传私聊文件，适合把本地文件、路径资源和附件发送到指定好友私聊会话

Args:
    file(str): 必填，资源路径或URL。
    name(str): 必填，文件名称。
    upload_file(bool): 必填，是否执行上传。
    user_id(int): 可选，对方 QQ 号。默认使用当前消息发送者的用户 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if name is not None:
            payload['name'] = name
        if upload_file is not None:
            payload['upload_file'] = upload_file
        payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'upload_private_file', payload)
