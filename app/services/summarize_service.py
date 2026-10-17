"""`/v1/summarize` 的业务实现（契约 §3）。"""

from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.core.text import split_for_summary
from app.models.schemas.summarize import SummarizeRequest
from app.prompts import summarize as prompt
from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)


def summarize(req: SummarizeRequest) -> str:
    settings = get_settings()
    llm = get_llm()
    title = req.title or "未命名笔记"
    
    t_start = time.time()
    
    # 1. 判断是否需要分治
    chunks = split_for_summary(
        req.content,
        chunk_size=settings.summary_chunk_size,
        overlap=settings.summary_chunk_overlap,
    )
    
    logger.info(
        "summarize 解析完成: 原文长度=%s, 分块数=%s, 耗时=%.2fs",
        len(req.content), len(chunks), time.time() - t_start
    )

    # 2. 短文本直接总结
    if len(chunks) == 1:
        logger.info("  ↳ 走短文本直出分支")
        t0 = time.time()
        messages = [
            {"role": "system", "content": prompt.SYSTEM},
            {"role": "user", "content": prompt.USER_TEMPLATE.format(title=title, content=chunks[0])},
        ]
        summary = llm.invoke(messages).strip()
        if not summary:
            raise RuntimeError("模型返回空摘要")
        logger.info("  ↳ 短文本总结完成: 耗时=%.2fs", time.time() - t0)
        return summary

    # 3. 长文本 Map 阶段（逐块总结）
    logger.info("  ↳ 进入长文本分治分支 (Map 阶段)")
    partial_summaries = []
    map_start = time.time()
    
    for i, chunk in enumerate(chunks):
        t0 = time.time()
        messages = [
            {"role": "system", "content": prompt.CHUNK_SYSTEM},
            {"role": "user", "content": prompt.CHUNK_USER_TEMPLATE.format(
                index=i + 1, total=len(chunks), content=chunk
            )},
        ]
        try:
            partial = llm.invoke(messages).strip()
            if partial:
                partial_summaries.append(partial)
            logger.info(
                "    块 %s/%s 完成: 原文=%s字, 摘要=%s字, 耗时=%.2fs",
                i + 1, len(chunks), len(chunk), len(partial), time.time() - t0
            )
        except Exception as exc:
            # 某一小块失败不应该导致整个长文总结失败，记下错误继续处理下一块
            logger.error("    块 %s/%s 失败: %s", i + 1, len(chunks), exc)

    if not partial_summaries:
        raise RuntimeError("所有分块总结均失败，无法生成摘要")

    # 4. 长文本 Reduce 阶段（合并总摘要）
    logger.info("  ↳ 进入 Reduce 阶段: 准备合并 %s 个片段摘要", len(partial_summaries))
    reduce_start = time.time()
    
    merged_text = "\n\n".join(partial_summaries)
    messages = [
        {"role": "system", "content": prompt.MERGE_SYSTEM},
        {"role": "user", "content": prompt.MERGE_USER_TEMPLATE.format(
            title=title, content=merged_text
        )},
    ]
    final_summary = llm.invoke(messages).strip()

    if not final_summary:
        raise RuntimeError("模型返回空的总摘要")

    logger.info(
        "  ↳ 长文本分治完成: Map耗时=%.2fs, Reduce耗时=%.2fs, 总耗时=%.2fs",
        reduce_start - map_start, time.time() - reduce_start, time.time() - t_start
    )
    return final_summary