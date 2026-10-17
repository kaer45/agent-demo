# app/services/query_processor.py
from __future__ import annotations

import logging

from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)


def process(raw_query: str, use_hyde: bool = False, use_mqe: bool = False) -> list[dict]:
    """返回一个或多个用于检索的 query 列表。
    
    返回格式：[{"query": "文本", "source": "original|hyde|mqe"}, ...]
    """
    # 1. 基础清洗：去 @bot
    query = raw_query.strip()
    if query.startswith("@bot"):
        query = query[4:].strip()
    
    if not query:
        return []

    results = [{"query": query, "source": "original"}]

    # 2. 多路扩展
    if use_hyde:
        logger.info("Query 策略: HyDE")
        hypo_doc = _generate_hypothetical_doc(query)
        results.append({"query": hypo_doc, "source": "hyde"})
        
    if use_mqe:
        logger.info("Query 策略: MQE")
        # 关键修改：MQE 基于用户原始的 query 扩展，不基于 hypo_doc！
        sub_queries = _expand_to_sub_queries(query)
        for sq in sub_queries:
            results.append({"query": sq, "source": "mqe"})

    return results


def _generate_hypothetical_doc(query: str) -> str:
    llm = get_llm()
    prompt = (
        "请针对以下问题，写一段简短的、事实性的回答（假设你是一个了解用户生活的人）。"
        "不要用“假设”、“可能”等词。\n"
        f"问题：{query}\n"
        "回答："
    )
    return llm.invoke([{"role": "user", "content": prompt}]).strip()


def _expand_to_sub_queries(query: str) -> list[str]:
    llm = get_llm()
    prompt = (
        "请将以下问题改写成 2 个不同角度的简短查询。"
        "直接输出改写后的查询，每行一个，不要序号，不要解释。\n"
        f"问题：{query}"
    )
    text = llm.invoke([{"role": "user", "content": prompt}]).strip()
    return [line.strip("- ").strip() for line in text.split("\n") if line.strip()][:2]