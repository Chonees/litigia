"""Local embeddings using sentence-transformers.

No API keys, no costs, runs on your machine.
multilingual-e5-base REQUIRES "query: " prefix for queries.
Documents were ingested without "passage: " prefix — the reranker compensates.
"""

from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

MODEL_NAME = "intfloat/multilingual-e5-base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        print(f"  Loading embedding model: {MODEL_NAME} on {DEVICE}...")
        _model = SentenceTransformer(MODEL_NAME, device=DEVICE)
        print(f"  Model loaded. Dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


async def get_embeddings(texts: list[str], prefix: str = "") -> list[list[float]]:
    """Generate embeddings locally. Use prefix='query: ' for search queries."""
    model = _get_model()
    prefixed = [f"{prefix}{t}" for t in texts] if prefix else texts
    embeddings = model.encode(
        prefixed,
        show_progress_bar=False,
        normalize_embeddings=True,
        batch_size=32 if DEVICE == "cpu" else 128,
        device=DEVICE,
    )
    return embeddings.tolist()


async def get_query_embedding(text: str) -> list[float]:
    """Embed a SEARCH QUERY with the required 'query: ' prefix."""
    result = await get_embeddings([text], prefix="query: ")
    return result[0]


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text (no prefix — backward compat)."""
    result = await get_embeddings([text])
    return result[0]


def embedding_dimension() -> int:
    """Get the dimension of the embedding model."""
    return _get_model().get_sentence_embedding_dimension()
