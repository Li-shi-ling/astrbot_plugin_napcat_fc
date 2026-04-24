from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass(frozen=True)
class NapCatClientConfig:
    base_url: str = "http://127.0.0.1:3000"
    access_token: str = ""
    timeout: float = 30.0


class NapCatClient:
    def __init__(self, config: NapCatClientConfig):
        self.config = config
        self._session: aiohttp.ClientSession | None = None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "NapCatClient":
        return cls(
            NapCatClientConfig(
                base_url=str(config.get("base_url") or "http://127.0.0.1:3000"),
                access_token=str(config.get("access_token") or ""),
                timeout=float(config.get("timeout") or 30.0),
            )
        )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(self, endpoint: str, payload: dict[str, Any] | None = None) -> str:
        if not self.config.base_url.strip():
            raise ValueError("NapCat base_url 未配置。")

        session = await self._get_session()
        url = self._build_url(endpoint)
        headers = {"Content-Type": "application/json"}
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"

        async with session.post(
            url,
            json=payload or {},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
        ) as response:
            text = await response.text()
            if response.status >= 400:
                raise RuntimeError(
                    f"NapCat 接口 {endpoint} 请求失败：HTTP {response.status} {text}"
                )
            return self._normalize_response(text)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _build_url(self, endpoint: str) -> str:
        action = endpoint.strip()
        if not action:
            raise ValueError("endpoint 不能为空。")
        if not action.startswith("/"):
            action = f"/{action}"
        return f"{self.config.base_url.rstrip('/')}{action}"

    @staticmethod
    def _normalize_response(text: str) -> str:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False)
        except json.JSONDecodeError:
            return text
