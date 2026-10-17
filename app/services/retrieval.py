"""检索：根据 query 从 Qdrant 找相关文档。

契约 §6：
- 共享问题（couple）→ 查 moment_c{scope_id}
- 个人问题（personal）→ 查 note_u{scope_id}

失败时降级为空列表，不抛异常——检索失败不该中断对话。
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.core.names import namespace_for_by_scope
from app.services import vector_store
from app.services.embedding_client import get_embedding

logger = logging.getLogger(__name__)


def retrieve(scope: str, scope_id: int, query: str, top_k: int | None = None) -> list[dict]:
    """检索相关文档。

    返回 list[dict]，每个 dict 含：
        score, biz_type, biz_id, title, content

    失败时返回空列表（降级，不中断对话）。
    """
    settings = get_settings()

    # 检索开关
    if not settings.retrieval_enabled:
        logger.info("检索已关闭")
        return []

    try:
        # 1. 按 scope 决定查哪个 collection
        namespace = namespace_for_by_scope(scope, scope_id)

        # 2. query 向量化
        vector = get_embedding().encode(query)

        # 3. 检索
        top_k = top_k or settings.retrieval_top_k
        results = vector_store.search(namespace, vector, top_k=top_k)
        # ================= 新增：详细检索日志 =================
        logger.info("【检索详情】ns=%s query='%s' 原始召回=%s 条", namespace, query[:20], len(results))
        
        # 截取前 5 条打印
        for i, r in enumerate(results[:5]):
            score = r["score"]
            payload = r.get("payload", {})
            content = payload.get("content", "")
            # 截断内容，防止刷屏（保留前 40 字）
            preview = content.replace("\n", " ")[:40] + ("..." if len(content) > 40 else "")
            
            logger.info("  [%s] score=%.4f | biz=%s:%s | content=%s", 
                        i + 1, score, payload.get("biz_type"), payload.get("biz_id"), preview)
        # ====================================================
        # 4. 过滤低分
        threshold = settings.retrieval_score_threshold
        
        docs = []
        for r in results:
            if r["score"] < threshold:
                continue
            payload = r["payload"] or {}
            docs.append({
                "score": r["score"],
                "biz_type": payload.get("biz_type"),
                "biz_id": payload.get("biz_id"),
                "title": _make_title(payload),
                "content": payload.get("content", ""),
            })

        logger.info(
            "检索: scope=%s scope_id=%s query_len=%s 命中=%s",
            scope, scope_id, len(query), len(docs),
        )
        return docs

    except Exception as exc:
        # 降级：检索失败不中断对话
        logger.exception("检索失败，降级为空上下文: %s", exc)
        return []


def _make_title(payload: dict) -> str:
    """没有 title 字段时，从 content 截前 30 字当标题。"""
    content = (payload.get("content") or "").strip()
    if not content:
        return ""
    return content[:30] + ("..." if len(content) > 30 else "")