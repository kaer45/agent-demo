"""插入一条数据到向量数据库（走 ingest_service）。"""

from __future__ import annotations

from app.models.schemas.ingest import IngestRequest
from app.services import ingest_service


def add(
    biz_type: str,
    biz_id: int,
    content: str,
    scope: str,
    scope_id: int,
) -> None:
    """插入一条数据，等价于调一次 /v1/ingest 的 upsert。

    Args:
        biz_type: moment / photo / note
        biz_id:   业务主键
        content:  要向量化的文本
        scope:    couple / personal
        scope_id: coupleId 或 userId
    """
    req = IngestRequest(
        trace_id="seed",
        biz_type=biz_type,
        biz_id=biz_id,
        content=content,
        scope=scope,
        scope_id=scope_id,
        action="upsert",
    )
    ingest_service.process(req)

if __name__=="__main__":
    add(
        biz_type="moment",
        biz_id=101,
        content="今天我给我的女朋友江家雪买了一杯奶茶，她很喜欢喝杨枝甘露",
        scope="couple",
        scope_id=1,
    )
    print("插入成功")