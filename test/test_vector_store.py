"""测试 Qdrant 的 upsert / delete / search。"""

from app.services import vector_store
from app.services.embedding_client import get_embedding
from app.core.names import point_id_for
NS = "test_ns_1"
PID = point_id_for("moment", 1)
NOT_EXIST_PID=point_id_for("moment",2)
TEXT = "今天一起看了日落，杭州西湖"

# 1. 嵌入
vec = get_embedding().encode(TEXT)
print("向量维度:", len(vec))

# 2. upsert
vector_store.upsert(
    namespace=NS,
    point_id=PID,
    vector=vec,
    payload={"biz_type": "moment", "biz_id": 1, "content": TEXT},
)
print("upsert 完成")

# 3. 幂等验证：再 upsert 一次
vector_store.upsert(
    namespace=NS,
    point_id=PID,
    vector=vec,
    payload={"biz_type": "moment", "biz_id": 1, "content": TEXT},
)
print("重复 upsert 完成")

# 4. search
results = vector_store.search(NS, vec, top_k=3)
print("检索结果数:", len(results))
for r in results:
    print("  score:", round(r["score"], 4), "content:", r["payload"].get("content"))

# 5. delete
vector_store.delete(NS, PID)
print("delete 完成")

# 6. delete 不存在的点（幂等）
vector_store.delete(NS, NOT_EXIST_PID)
print("delete 不存在的点：OK")

# 7. 再 search，应该为空
results = vector_store.search(NS, vec, top_k=3)
print("删除后检索结果数:", len(results))