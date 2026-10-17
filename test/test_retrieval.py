"""测试检索：用不同 query 看召回什么。"""

from app.services import retrieval


def show(query: str, scope: str, scope_id: int, top_k: int = 3) -> None:
    docs = retrieval.retrieve(scope, scope_id, query, top_k=top_k)
    print(f"\nquery={query!r}  scope={scope}/{scope_id}")
    if not docs:
        print("  （无召回）")
        return
    for d in docs:
        print(f"  [{d['score']:.4f}] {d['content'][:40]}")


if __name__ == "__main__":
    print("=" * 60)
    print("couple 域检索（应该只召回相关动态）")
    print("=" * 60)

    show("户外运动", "couple", 11)
    show("做饭", "couple", 11)
    show("电影", "couple", 11)
    show("旅行照片", "couple", 11)

    print()
    print("=" * 60)
    print("personal 域检索（应该只召回相关笔记）")
    print("=" * 60)

    show("数据库", "personal", 1)
    show("多线程", "personal", 1)
    show("算法", "personal", 1)

    print()
    print("=" * 60)
    print("不相关的 query（应该召回 0 条）")
    print("=" * 60)

    show("量子物理", "couple", 11)
    show("今天天气怎么样", "personal", 1)