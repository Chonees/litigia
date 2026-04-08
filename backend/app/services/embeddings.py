"""Local embeddings using sentence-transformers.

No API keys, no costs, runs on your machine.
Model: BAAI/bge-m3 — state-of-the-art multilingual, excellent for Spanish legal text.
"""

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

# bge-m3 is 2GB and slow. bge-base-en-v1.5 is 400MB and 5x faster.
# For Spanish legal: intfloat/multilingual-e5-large — good multilingual, 1.2GB, fast on GPU
MODEL_NAME = "intfloat/multilingual-e5-base"  # 900MB, great Spanish, fast on 4090 Laptop


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (downloads on first use, ~2GB)."""
    global _model
    if _model is None:
        print(f"  Loading embedding model: {MODEL_NAME} (first time downloads ~2GB)...")
        _model = SentenceTransformer(MODEL_NAME)
        print(f"  Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings locally."""
    model = _get_model()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
        batch_size=128,  # GPU batch — 4090 Laptop 12GB VRAM, smaller model fits
        device="cuda",
    )
    return embeddings.tolist()


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    result = await get_embeddings([text])
    return result[0]


def embedding_dimension() -> int:
    """Get the dimension of the embedding model."""
    return _get_model().get_sentence_embedding_dimension()
