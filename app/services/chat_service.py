"""`/v1/chat` 的业务实现：会话记忆 + 检索增强 + 流式产出。

事件流：
    ("delta", "增量文本")   ← 可多次
    ("refs", [ {...} ])     ← 可选
    ("error", "错误信息")    ← 仅出错时
"""

from __future__ import annotations

import logging
from typing import Iterator

from app.config import get_settings
from app.models.schemas.chat import ChatRequest
from app.prompts import chat as chat_prompt
from app.services import query_processor, retrieval, session_store
from app.services.llm_client import get_llm

logger = logging.getLogger(__name__)

ChatEvent = tuple[str, object]


def _session_key(req: ChatRequest) -> str:
    """契约 §2.3：按 user_id+session_id 维护会话。"""
    return f"{req.user_id}:{req.session_id}"


def run(req: ChatRequest) -> Iterator[ChatEvent]:
    settings = get_settings()
    session_key = _session_key(req)

    # 1. 读历史
    history = session_store.history(session_key, settings.session_max_turns)

    # 2. 处理 Query（获取原问题 + 扩展问题）
    use_hyde = getattr(settings, "retrieval_use_hyde", False)
    use_mqe = getattr(settings, "retrieval_use_mqe", False)
    
    # 返回格式：[{"query": "xxx", "source": "original"}, {"query": "yyy", "source": "hyde"}]
    query_infos = query_processor.process(req.message, use_hyde=use_hyde, use_mqe=use_mqe)
    
    # 提取清洗后的原问题（用于落库和发给大模型）
    cleaned_message = req.message.strip()
    for q in query_infos:
        if q["source"] == "original":
            cleaned_message = q["query"]
            break

    # 3. 多路召回合并去重（精准去重 + 取最高分）
    doc_map: dict[str, dict] = {}   # 用 dict 替代 set，实现“同 key 取最高分”
    logger.info("[检索阈值]=%s",settings.retrieval_score_threshold)
    for q_info in query_infos:
        q_text = q_info["query"]
        source = q_info["source"]
        
        docs = retrieval.retrieve(req.scope, req.scope_id or 0, q_text)
        
        for d in docs:
            doc_key = f"{d['biz_type']}:{d['biz_id']}"
            
            if doc_key not in doc_map:
                # 第一次遇到这条数据
                d["_retrieval_source"] = source
                doc_map[doc_key] = d
            else:
                # 已经存在：比较得分，如果新得分更高，替换并更新来源
                if d["score"] > doc_map[doc_key]["score"]:
                    d["_retrieval_source"] = source
                    doc_map[doc_key] = d

    # 将去重后的字典转回列表，按最终选出的最高分重新排序，截取 top_k
    all_docs = list(doc_map.values())
    all_docs.sort(key=lambda x: x["score"], reverse=True)
    final_docs = all_docs[:settings.retrieval_top_k]

    # 4. 拼 messages：system + history + user
    system = chat_prompt.build_system_prompt(final_docs)
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    
    # 送给大模型的是清洗后的提问
    messages.append({"role": "user", "content": cleaned_message})

    logger.info(
        "chat 开始: session=%s scope=%s scope_id=%s history=%s refs=%s",
        session_key, req.scope, req.scope_id, len(history), len(final_docs),
    )
    
    # 可以加一行调试日志，看看多路召回合并后到底留下了什么
    for d in final_docs:
        logger.info("  引用来源: score=%.4f source=%s biz=%s", d["score"], d.get("_retrieval_source"), d["biz_id"])

    # 5. 先落用户提问（存清洗后的文本）
    session_store.append(session_key, "user", cleaned_message)

    # 6. 流式生成，收集已产出内容
    collected: list[str] = []
    try:
        for delta in get_llm().stream(messages):
            collected.append(delta)
            yield ("delta", delta)
    except Exception as exc:
        logger.exception("LLM 调用失败")
        yield ("error", str(exc))
        return
    finally:
        # 无论成功、失败还是被中断，都把已产出的部分落库
        answer = "".join(collected).strip()
        if answer:
            session_store.append(session_key, "assistant", answer)
            logger.info("chat 结束: 已保存回答 %s 字", len(answer))

    # 7. refs 事件（只返回业务需要的字段）
    if final_docs:
        yield ("refs", [
            {
                "biz_type": d["biz_type"],
                "biz_id": d["biz_id"],
                "title": d["title"],
            }
            for d in final_docs
        ])