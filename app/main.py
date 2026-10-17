# 实现创建 fastapi 应用，注册路由

from __future__ import annotations

from app.logging_conf import setup_logging

setup_logging("INFO")

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app import __version__
from app.api.routes import chat, health, ingest, summarize
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.dependencies import verify_key

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动：初始化资源")

    # 初始化 SQLite
    from app.services import session_store
    session_store.init_db()
    app.state.ready = True

    yield

    # 关闭时释放资源
    logger.info("关闭：释放资源")
    _close_all()


def _close_all() -> None:
    """尽力关闭所有外部连接，失败不影响退出。"""
    for name, getter in [
        ("Qdrant", lambda: __import__(
            "app.services.vector_store", fromlist=["_client"]
        )._client()),
        ("Embedding", lambda: __import__(
            "app.services.embedding_client", fromlist=["get_embedding"]
        ).get_embedding()),
        ("LLM", lambda: __import__(
            "app.services.llm_client", fromlist=["get_llm"]
        ).get_llm()),
    ]:
        try:
            target = getter()
            closer = getattr(target, "close", None)
            if callable(closer):
                closer()
                logger.info("%s 已关闭", name)
        except Exception as exc:
            logger.warning("关闭 %s 失败: %s", name, exc)


app = FastAPI(
    title="couple-site Agent 服务",
    version=__version__,
    description=(
        "couple-site 的 Python 侧 Agent 服务，为 Java 提供 AI 能力。\n\n"
        "**接口清单**：\n\n"
        "- `POST /v1/chat`：SSE 流式对话（检索增强 + 多轮记忆）\n"
        "- `POST /v1/summarize`：内容摘要（支持长文本分治）\n"
        "- `POST /v1/ingest`：业务数据向量同步（幂等）\n"
        "- `GET /v1/health`：服务与依赖自检\n\n"
        "**鉴权**：所有 `/v1/*` 接口需携带请求头 `X-Agent-Key`。"
    ),
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.get("/", tags=["root"], summary="服务信息")
async def root():
    return {
        "service": "couple-site Agent 服务",
        "version": __version__,
        "docs": "/docs",
        "health": "/v1/health",
    }


_auth = [Depends(verify_key)]
app.include_router(health.router, dependencies=_auth)
app.include_router(chat.router, dependencies=_auth)
app.include_router(summarize.router, dependencies=_auth)
app.include_router(ingest.router, dependencies=_auth)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        # reload=(settings.log_level == "DEBUG"),
        reload=True,
        log_level=settings.log_level.lower(),
    )