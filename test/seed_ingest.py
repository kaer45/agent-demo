"""往 Qdrant 里灌测试数据，用于验证检索。

用法：
    python -m test.seed_ingest              # 灌默认数据
    python -m test.seed_ingest clean        # 清空所有测试 collection
"""

from __future__ import annotations

import sys
import uuid

from app.core.names import namespace_for, point_id_for
from app.services import vector_store
from app.services.embedding_client import get_embedding

# ---------- 测试数据 ----------
# 每条：(biz_type, biz_id, scope, scope_id, content)
SEED_DATA = [
    # couple 域：情侣动态（应该只召回语义相关的）
    ("moment", 1, "couple", 11, "今天去爬山，看了日出，山顶风很大但景色很美"),
    ("moment", 2, "couple", 11, "晚上在家做了番茄炒蛋，配米饭，很简单的一顿"),
    ("moment", 3, "couple", 11, "去电影院看了新上映的科幻片，剧情有点烧脑"),
    ("photo", 4, "couple", 11, "相册名：2024旅行 照片描述：洱海边拍的落日"),

    # personal 域：个人笔记
    ("note", 101, "personal", 1, "Redis 是一种基于内存的键值数据库，支持持久化"),
    ("note", 102, "personal", 1, "Python 的 GIL 导致多线程无法真正并行执行 CPU 密集型任务"),
    ("note", 103, "personal", 1, "二分查找的时间复杂度是 O(log n)，前提是数组有序"),
]


def seed() -> None:
    """写入所有测试数据。"""
    emb = get_embedding()

    for biz_type, biz_id, scope, scope_id, content in SEED_DATA:
        namespace = namespace_for(biz_type, scope, scope_id)
        point_id = point_id_for(biz_type, biz_id)

        vector = emb.encode(content)
        vector_store.upsert(
            namespace=namespace,
            point_id=point_id,
            vector=vector,
            payload={
                "biz_type": biz_type,
                "biz_id": biz_id,
                "scope": scope,
                "scope_id": scope_id,
                "content": content,
                "created_at": "2026-10-16T00:00:00+00:00",
            },
        )
        print(f"  ✅ {namespace} / {biz_type}:{biz_id}  {content[:30]}")

    print()
    print(f"完成，共写入 {len(SEED_DATA)} 条")


def clean() -> None:
    """删掉测试数据涉及的所有 collection。"""
    from app.services.vector_store import _client

    namespaces = sorted({namespace_for(bt, sc, sid) for bt, _, sc, sid, _ in SEED_DATA})
    client = _client()

    for ns in namespaces:
        if client.collection_exists(ns):
            client.delete_collection(ns)
            print(f"  🗑️  删除 collection: {ns}")
        else:
            print(f"  ⏭️  跳过（不存在）: {ns}")

    print()
    print("清理完成")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        seed()