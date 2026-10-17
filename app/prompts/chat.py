"""对话 system prompt 与上下文拼装。"""

from __future__ import annotations

SYSTEM = """你是「情侣空间」里的 AI 助手，名字叫小空。
你的服务对象是一对情侣，语气亲切、自然、简洁。

规则：
1. 用中文回答；
2. 不要提及你是由哪个模型提供的；
3. 如果提供了「参考资料」，优先依据它回答，并在相应句末用 [1] [2] 标注来源；
4. 参考资料不足以回答时，如实说明，绝不编造。"""

CONTEXT_HEADER = "以下是可参考的资料（可能不完整，仅供参照）："
CONTEXT_ITEM = "[{idx}] {title}\n{content}"
NO_CONTEXT = "（本次没有检索到相关资料，请基于你的通用知识回答）"


def build_system_prompt(docs: list[dict]) -> str:
    """把检索结果拼进 system prompt。docs 为空则明确告知没有资料。"""
    if not docs:
        return f"{SYSTEM}\n\n{NO_CONTEXT}"

    lines = [SYSTEM, "", CONTEXT_HEADER]
    for idx, doc in enumerate(docs, start=1):
        lines.append(
            CONTEXT_ITEM.format(
                idx=idx,
                title=doc.get("title") or "未命名",
                content=doc.get("content", ""),
            )
        )
    return "\n".join(lines)