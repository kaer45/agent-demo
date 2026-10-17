from qdrant_client import QdrantClient
from app.config import get_settings

settings = get_settings()

client=QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
    timeout=settings.qdrant_timeout
)

print(client.get_collections())