"""文本处理：截断与分块。"""

from __future__ import annotations

import re


def split_for_summary(
    content: str,
    chunk_size: int = 6000,
    overlap: int = 500,
) -> list[str]:
    """将长文本按段落边界切分成多个块。
    
    如果文本长度 <= chunk_size，直接返回原文本的单元素列表。
    """
    if len(content) <= chunk_size:
        return [content]

    # 优先按双换行（段落）切分，保留 Markdown 代码块/公式的完整性
    paragraphs = re.split(r"\n\s*\n", content)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # 如果单段就超过 chunk_size，只能硬切
        if len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # 硬切长段落
            for i in range(0, len(para), chunk_size - overlap):
                chunks.append(para[i:i + chunk_size].strip())
            continue

        # 正常累加段落
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            # 当前块满了，保存起来
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # 开启新块，带上上一块尾部的 overlap 字符
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:]
                current_chunk = tail + "\n\n" + para + "\n\n"
            else:
                current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks