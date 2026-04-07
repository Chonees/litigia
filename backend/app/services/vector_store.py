from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from app.core.config import settings


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(client: QdrantClient | None = None) -> None:
    """Create the jurisprudencia collection if it doesn't exist."""
    client = client or get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )


def build_filter(
    jurisdiccion: str | None = None,
    fuero: str | None = None,
    materia: str | None = None,
    source: str | None = None,
) -> Filter | None:
    """Build a Qdrant filter from optional parameters."""
    conditions = []
    if jurisdiccion:
        conditions.append(FieldCondition(key="jurisdiccion", match=MatchValue(value=jurisdiccion)))
    if fuero or materia:
        # materia and fuero map to the same field in our schema
        value = materia or fuero
        conditions.append(FieldCondition(key="materia", match=MatchValue(value=value)))
    if source:
        conditions.append(FieldCondition(key="source", match=MatchValue(value=source)))

    return Filter(must=conditions) if conditions else None


async def search_similar(
    query_embedding: list[float],
    top_k: int = 5,
    jurisdiccion: str | None = None,
    fuero: str | None = None,
    materia: str | None = None,
    source: str | None = None,
    client: QdrantClient | None = None,
) -> list[dict]:
    """Search for similar documents in Qdrant."""
    client = client or get_qdrant_client()

    query_filter = build_filter(
        jurisdiccion=jurisdiccion, fuero=fuero, materia=materia, source=source
    )

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_embedding,
        query_filter=query_filter,
        limit=top_k,
    )

    return [
        {
            "id": str(point.id),
            "score": point.score,
            **point.payload,
        }
        for point in results.points
    ]
