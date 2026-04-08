"""Local embeddings using sentence-transformers.

No API keys, no costs, runs on your machine.
Model: BAAI/bge-m3 — state-of-the-art multilingual, excellent for Spanish legal text.
"""

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

MODEL_NAME = "BAAI/bge-m3"


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
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


async def get_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    result = await get_embeddings([text])
    return result[0]


def embedding_dimension() -> int:
    """Get the dimension of the embedding model."""
    return _get_model().get_sentence_embedding_dimension()
