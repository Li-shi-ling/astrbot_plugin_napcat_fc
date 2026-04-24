from __future__ import annotations

import json
from typing import Any


async def call_aiocqhttp_action(event: Any, endpoint: str, payload: dict[str, Any]) -> str:
    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
        AiocqhttpMessageEvent,
    )

    if not isinstance(event, AiocqhttpMessageEvent):
        raise ValueError("NapCat 函数工具只能在 aiocqhttp/NapCat 消息事件中调用。")
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象。")

    action = endpoint.strip().lstrip("/")
    if not action:
        raise ValueError("endpoint 不能为空。")

    bot = event.bot
    api = getattr(bot, "api", None)
    call_action = getattr(api, "call_action", None) or getattr(bot, "call_action", None)
    if not call_action:
        raise RuntimeError("当前 aiocqhttp bot 不支持 call_action。")

    result = await call_action(action, **payload)
    return json.dumps(result, ensure_ascii=False, default=str)
