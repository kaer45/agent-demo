"""`POST /v1/summarize` —— 内容摘要（契约 §3）。

普通 JSON 接口，不是 SSE：
- 成功：HTTP 200，body `{code:0, message:"success", data:{summary:"..."}}`
- 失败：HTTP 4xx/5xx，body 同样是信封（由全局异常处理器统一转换）

⚠️ 路由用普通 `def`，不是 `async def`：service 内部是同步阻塞调用
（HelloAgentsLLM.invoke 可能等几十秒），写成 async def 会卡死整个事件循环。
FastAPI 会把 `def` 路由整体丢进线程池，不阻塞其他请求。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.logging_conf import set_trace
from app.models.schemas.summarize import SummarizeRequest
from app.services import summarize_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1",tags=["summarize"])

@router.post(
    "/summarize",
    summary="内容摘要",
    description="把笔记正文发给模型生成摘要，返回完整 JSON（非流式）。",
)
def summarize(req:SummarizeRequest) -> dict:
    set_trace(req.trace_id)
    logger.info(
        "summarize 开始: note_id=%s title=%s content_len=%s",
        req.note_id,
        req.title,
        len(req.content),
    )
    summary = summarize_service.summarize(req)
    logger.info(summary)
    return {"code": 0, "message": "success", "data": {"summary": summary}}