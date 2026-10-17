"""LLM 客户端（OpenAI SDK），提供全局单例。"""

from __future__ import annotations

import logging
from typing import Iterator

from app.config import Settings, get_settings

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """同步 LLM 客户端。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client=OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout,
        )
        self._model=self.settings.llm_model_id

    # ---------- 状态 ----------
    def describe(self) -> dict:
        return {
            "model": self.settings.llm_model_id,
            "base_url": self.settings.llm_base_url,
            "ready": self.settings.llm_configured,
        }


    # ---------- 对外接口 ----------
    def stream(self, messages: list[dict[str, str]], min_chars: int = 8) -> Iterator[str]:
        """流式产出文本增量。攒够 min_chars 才 yield，减少 SSE 事件数。"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )
        buffer = ""
        for chunk in response:
            content = chunk.choices[0].delta.content
            if not content:
                continue
            buffer += content
            if len(buffer) >= min_chars:
                yield buffer
                buffer = ""
        if buffer:
            yield buffer

    def invoke(self, messages: list[dict[str, str]], **kwargs) -> str:
        """一次性拿到完整回答（摘要用）。"""
        response=self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=False,
            **kwargs
        )
        return (response.choices[0].message.content or "").strip()

    def close(self) -> None:
        """释放底层 HTTP 连接。"""
        try:
            self._client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 进程内单例
# ---------------------------------------------------------------------------
_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm() -> None:
    """测试用：清掉单例。"""
    global _client
    if _client is not None:
        _client.close()
    _client = None