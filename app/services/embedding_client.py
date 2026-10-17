"""DashScope 嵌入客户端（OpenAI 兼容 REST）。

不做静默降级：失败就抛异常，让路由返回 5xx。
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self)->None:
        settings=get_settings()
        self._url=f"{settings.dashscope_base_url.rstrip('/')}/embeddings"
        self._api_key=settings.dashscope_api_key
        self._model = settings.embed_model_name
        self._client = httpx.Client(timeout=30)
    def encode(self, text: str) -> list[float]:
        """文本 → 向量。失败抛异常，不做静默降级。"""
        resp = self._client.post(
            self._url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self._model, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def close(self) -> None:
        self._client.close()

@lru_cache(maxsize=1)
def get_embedding() -> EmbeddingClient:
    return EmbeddingClient()
    