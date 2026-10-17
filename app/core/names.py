"""namespace 与 point id 生成的唯一出处。"""

from __future__ import annotations

import uuid


def namespace_for(biz_type: str, scope: str, scope_id: int) -> str:
    """按契约 §6 的映射规则返回 Qdrant collection 名。"""
    if biz_type in ("moment", "photo") and scope == "couple":
        return f"moment_c{scope_id}"
    if biz_type == "note" and scope == "personal":
        return f"note_u{scope_id}"
    raise ValueError(f"不支持的 biz_type/scope 组合: {biz_type}/{scope}")


def namespace_for_by_scope(scope: str, scope_id: int) -> str:
    """检索时用：只知道 scope 和 scope_id，不知道具体 biz_type。

    couple → moment_c{scope_id}（moment 和 photo 同域）
    personal → note_u{scope_id}
    """
    if scope == "couple":
        return f"moment_c{scope_id}"
    if scope == "personal":
        return f"note_u{scope_id}"
    raise ValueError(f"不支持的 scope: {scope}")


def point_id_for(biz_type: str, biz_id: int) -> str:
    """确定性 point id：同 biz_type+biz_id 永远映射到同一个 id。
    这样重复 upsert 会覆盖同一个点，delete 也能精确命中。
    用 UUID5 保证跨进程确定性。
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{biz_type}:{biz_id}"))