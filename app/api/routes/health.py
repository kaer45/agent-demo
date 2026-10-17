"""`GET /v1/health` —— 探活与自检（契约 §4）。

Java **不主动轮询**本接口（它只靠调用结果判定），这里主要给人看和给容器做存活检查。
因为是同步 `def`，FastAPI 会把它整体丢进线程池，不会阻塞事件循环。

设计原则：**按能力降级，不 fail-fast**。
Qdrant / 嵌入模型不可用时只有 ingest 与检索受影响，chat / summarize 照常工作，
所以 health 也不该直接 5xx，而是把各组件状态如实报出来，由调用方判断。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from app.config import get_settings
from app import __version__

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health", summary="探活与依赖自检")
def health() -> dict:
    settings=get_settings()

    # 各依赖的配置是否就绪
    components={
        "llm":settings.llm_configured,
        "embedding":settings.embedding_configured,
        "qdrant":bool(settings.qdrant_url),
    }

    # 只要LLM不可用，chat/summarize 不可用，需要降级
    degraded = not components["llm"]

    return {
        "code":0,
        "message":"ok",
        "data":{
            "version":__version__,
            "degraded":degraded,
            "components":components,
            "config":settings.summary(),
        },
    }
