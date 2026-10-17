"""`POST /v1/chat` —— 对话 SSE（契约 §2.2）。

SSE 格式：
    data: {"content":"增量"}\n\n
    data: {"refs":[...]}\n\n          （可选）
    data: {"error":"人类可读信息"}\n\n （仅出错时）
    data: [DONE]\n\n                   （必须发）
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import verify_key
from app.models.schemas.chat import ChatRequest
from app.services import chat_service
from app.logging_conf import set_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


def _event(payload: dict) -> str:
    """一个 SSE 事件：`data: <json>` + 两个换行。

    ensure_ascii=False：否则中文变成 \\uXXXX，抓包和日志都没法看。
    """
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse(req: ChatRequest) -> Iterator[str]:
    events = chat_service.run(req)
    trace = req.trace_id

    try:
        while True:
            # 每次恢复执行都可能换了线程，所以每次 next() 前都重设一次
            set_trace(trace)
            try:
                kind, payload = next(events)
            except StopIteration:
                break
            except Exception as exc:
                logger.exception("对话未捕获异常")
                yield _event({"error": "AI 服务内部错误"})
                break

            if kind == "delta":
                yield _event({"content": payload})
            elif kind == "refs":
                yield _event({"refs": payload})
            elif kind == "error":
                yield _event({"error": payload})
    finally:
        set_trace(trace)
        events.close()

    yield "data: [DONE]\n\n"


@router.post("/chat", summary="对话（SSE 流式）", dependencies=[Depends(verify_key)])
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _sse(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 防止 Nginx 等反代缓冲 SSE
            "X-Accel-Buffering": "no",
        },
    )