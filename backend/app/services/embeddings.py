import httpx

from app.core.config import settings

OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI text-embedding-3-large.

    Batches up to 2048 texts per request (OpenAI limit).
    """
    all_embeddings: list[list[float]] = []
    batch_size = 2048

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.post(
                OPENAI_EMBEDDING_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "input": batch,
                    "model": settings.anthropic_embedding_model,
                    "dimensions": settings.embedding_dimensions,
                },
            )
            response.raise_for_status()
            data = response.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    result = await get_embeddings([text])
    return result[0]
