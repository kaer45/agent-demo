"""`POST /v1/ingest` —— 业务数据向量同步（契约 §1）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.logging_conf import bind_trace
from app.models.schemas.ingest import IngestRequest
from app.services import ingest_service

logger = logging.getLogger(__name__)

router=APIRouter(prefix="/v1",tags=["ingest"])

@router.post("/ingest", summary="向量同步")
def ingest(req: IngestRequest) -> dict:
    with bind_trace(req.trace_id):
        logger.info(
            "ingest 开始: biz=%s:%s action=%s scope=%s/%s",
            req.biz_type, req.biz_id, req.action, req.scope, req.scope_id,
        )
        ingest_service.process(req)
    return {"code": 0, "message": "success", "data": None}