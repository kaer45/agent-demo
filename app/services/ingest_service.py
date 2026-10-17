"""`/v1/ingest` 的业务实现（契约 §1）。"""

from __future__ import annotations

import logging

from datetime import datetime, timezone

from app.core.names import namespace_for, point_id_for
from app.models.schemas.ingest import IngestRequest
from app.services import vector_store
from app.services.embedding_client import get_embedding

logger = logging.getLogger(__name__)


def process(req: IngestRequest) -> None:
    """处理一条 ingest 事件。upsert 写入向量，delete 删除向量。"""
    namespace = namespace_for(req.biz_type, req.scope, req.scope_id)
    point_id = point_id_for(req.biz_type, req.biz_id)

    if req.action == "upsert":
        vector = get_embedding().encode(req.content or "")
        vector_store.upsert(
            namespace=namespace,
            point_id=point_id,
            vector=vector,
            payload={
                "biz_type": req.biz_type,
                "biz_id": req.biz_id,
                "scope": req.scope,
                "scope_id": req.scope_id,
                "content": req.content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("ingest upsert: ns=%s point=%s", namespace, point_id)

    elif req.action == "delete":
        vector_store.delete(namespace=namespace, point_id=point_id)
        logger.info("ingest delete: ns=%s point=%s", namespace, point_id)

    else:
        raise ValueError(f"不支持的 action: {req.action}")