from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

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


async def upsert_documents(
    documents: list[dict],
    embeddings: list[list[float]],
    client: QdrantClient | None = None,
) -> None:
    """Insert or update documents in Qdrant."""
    client = client or get_qdrant_client()
    ensure_collection(client)

    points = [
        PointStruct(
            id=doc["id"],
            vector=embedding,
            payload={
                "tribunal": doc.get("tribunal", ""),
                "fecha": doc.get("fecha", ""),
                "caratula": doc.get("caratula", ""),
                "texto": doc.get("texto", ""),
                "materia": doc.get("materia", ""),
                "voces": doc.get("voces", []),
                "fuero": doc.get("fuero", ""),
                "jurisdiccion": doc.get("jurisdiccion", ""),
                "source": doc.get("source", ""),
                "source_id": doc.get("source_id", ""),
            },
        )
        for doc, embedding in zip(documents, embeddings)
    ]

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=settings.qdrant_collection, points=batch)


async def search_similar(
    query_embedding: list[float],
    top_k: int = 5,
    filters: dict | None = None,
    client: QdrantClient | None = None,
) -> list[dict]:
    """Search for similar documents in Qdrant."""
    client = client or get_qdrant_client()

    query_filter = None
    if filters:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = []
        for key, value in filters.items():
            if value:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if conditions:
            query_filter = Filter(must=conditions)

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
