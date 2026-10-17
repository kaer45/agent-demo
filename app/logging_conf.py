"""日志配置：统一格式，并支持把 trace_id 注入每条日志。

Java 每次请求都会带一个 16 位小写十六进制的 trace_id（契约 §0）。
路由收到后调用 `bind_trace(trace_id)`，本模块的 filter 就会把它写进日志行，
这样跨 Java / Python 排查同一次请求时能直接 grep。
"""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

# 默认 "-" 表示非请求上下文（例如启动阶段）
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


# 这些库在 INFO 级别噪音很大，统一压到 WARNING
_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "urllib3",
    "qdrant_client",
    "neo4j",
    "openai",
    "asyncio",
)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s [%(trace_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(TraceIdFilter())

    root = logging.getLogger()
    root.handlers[:] = [handler]  # 覆盖 uvicorn 默认 handler，避免日志重复
    root.setLevel(level.upper())

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def set_trace(trace_id: str | None) -> None:
    """只设置、不恢复。

    ⚠️ 专供**跨线程池**的 SSE 生成器使用。原因：
    Starlette 的 `StreamingResponse` 会把同步生成器交给 `iterate_in_threadpool`，
    它对每一次 `next()` 都单独发起一次 `anyio.to_thread.run_sync`，
    也就是**每一步都可能落在不同的工作线程、拿到不同的 context 副本**。
    而 `ContextVar.set()` 返回的 token 只能在**同一个 Context** 里 reset，
    否则抛：
        ValueError: Token ... was created in a different Context
    所以流式场景改用「每一步都重设一次」，完全不依赖恢复。
    """

    trace_id_var.set(trace_id or "-")


@contextmanager
def bind_trace(trace_id: str | None) -> Iterator[None]:
    """在 with 块内把所有日志都打上 trace_id。

    用「保存旧值 + 恢复」而不是 ContextVar token —— token 的 reset 要求
    set/reset 在同一个 Context 内，跨 Context 会抛 ValueError（见 set_trace 说明）。
    本函数适用于「一次调用同一 Context 内跑完」的场景，例如同步路由与 lifespan。
    """
    previous = trace_id_var.get()
    set_trace(trace_id)
    try:
        yield
    finally:
        set_trace(previous)


def current_trace() -> str:
    return trace_id_var.get()
