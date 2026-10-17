"""Qdrant 薄封装：按 namespace 隔离 collection。"""

from __future__ import annotations

import logging
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams,PointIdsList

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(
        url=s.qdrant_url,
        api_key=s.qdrant_api_key or None,
        timeout=s.qdrant_timeout,
    )


def _ensure_collection(name: str) -> None:
    s = get_settings()
    client = _client()
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=s.embed_dim, distance=Distance.COSINE),
        )
        logger.info("创建 collection: %s", name)


def upsert(namespace: str, point_id: str, vector: list[float], payload: dict) -> None:
    _ensure_collection(namespace)
    _client().upsert(
        collection_name=namespace,
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )


def delete(namespace: str, point_id: str) -> None:
    client = _client()
    if not client.collection_exists(namespace):
        return
    client.delete(collection_name=namespace, points_selector=PointIdsList(points=[point_id]),)


def search(namespace: str, vector: list[float], top_k: int = 4) -> list[dict]:
    client = _client()
    if not client.collection_exists(namespace):
        return []
    response = client.query_points(
        collection_name=namespace,
        query=vector,
        limit=top_k,
    )
    return [
        {"score": p.score, "payload": p.payload}
        for p in response.points
    ]