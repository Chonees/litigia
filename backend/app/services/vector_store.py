"""Vector store abstraction using ChromaDB.

ChromaDB runs embedded — no server, no Docker, no setup.
Data persists to D:/litigia-data/chromadb/.
"""

import chromadb

from app.core.config import settings

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    """Get or create the ChromaDB persistent client."""
    global _client
    if _client is None:
        persist_dir = str(settings.data_root / "chromadb")
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client


def get_collection() -> chromadb.Collection:
    """Get or create the jurisprudencia collection."""
    client = get_client()
    return client.get_or_create_collection(
        name=settings.qdrant_collection,
        metadata={"hnsw:space": "cosine"},
    )


def build_where_filter(
    jurisdiccion: str | None = None,
    fuero: str | None = None,
    materia: str | None = None,
    source: str | None = None,
) -> dict | None:
    """Build a ChromaDB where filter from optional parameters."""
    conditions = []
    if jurisdiccion:
        conditions.append({"jurisdiccion": jurisdiccion})
    if fuero or materia:
        conditions.append({"materia": materia or fuero})
    if source:
        conditions.append({"source": source})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


async def upsert_documents(
    doc_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Insert or update documents in ChromaDB."""
    collection = get_collection()

    # ChromaDB handles batching internally but we chunk to avoid memory spikes
    batch_size = 500
    for i in range(0, len(doc_ids), batch_size):
        end = i + batch_size
        collection.upsert(
            ids=doc_ids[i:end],
            embeddings=embeddings[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )


async def search_similar(
    query_embedding: list[float],
    top_k: int = 5,
    jurisdiccion: str | None = None,
    fuero: str | None = None,
    materia: str | None = None,
    source: str | None = None,
) -> list[dict]:
    """Search for similar documents."""
    collection = get_collection()

    where = build_where_filter(
        jurisdiccion=jurisdiccion, fuero=fuero, materia=materia, source=source
    )

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    if not results["ids"] or not results["ids"][0]:
        return []

    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else 0.0
        # ChromaDB returns distance (lower = better), convert to similarity score
        score = 1.0 - distance

        output.append({
            "id": doc_id,
            "score": score,
            "texto": results["documents"][0][i] if results["documents"] else "",
            **metadata,
        })

    return output


def collection_count() -> int:
    """Get the number of documents in the collection."""
    return get_collection().count()
