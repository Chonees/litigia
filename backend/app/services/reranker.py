"""Cross-encoder reranker for search results.

Uses BAAI/bge-reranker-v2-m3 to score (query, document) pairs.
Runs locally on GPU — $0 cost, ~200ms for 50 docs.
Compensates for documents ingested without E5 "passage:" prefix.
"""

from __future__ import annotations

import torch
from sentence_transformers import CrossEncoder

_reranker: CrossEncoder | None = None

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _get_reranker() -> CrossEncoder:
    """Lazy-load the reranker model."""
    global _reranker
    if _reranker is None:
        print(f"  Loading reranker: {RERANKER_MODEL} on {DEVICE}...", flush=True)
        _reranker = CrossEncoder(RERANKER_MODEL, device=DEVICE)
        print(f"  Reranker loaded.", flush=True)
    return _reranker


def rerank(query: str, documents: list[dict], top_k: int | None = None) -> list[dict]:
    """Rerank documents by cross-encoder relevance to query.

    Args:
        query: The search query
        documents: List of dicts with at least 'texto' or 'caratula' + 'sumario'
        top_k: Return only top K results (None = return all, sorted)

    Returns:
        Documents sorted by reranker score, with 'rerank_score' added.
    """
    if not documents:
        return documents

    reranker = _get_reranker()

    # Build (query, passage) pairs
    pairs = []
    for doc in documents:
        # Use caratula + sumario + first 500 chars of texto for ranking
        passage_parts = []
        if doc.get("caratula"):
            passage_parts.append(doc["caratula"])
        if doc.get("sumario"):
            passage_parts.append(doc["sumario"][:300])
        if doc.get("texto"):
            passage_parts.append(doc["texto"][:500])
        passage = " ".join(passage_parts) or "N/D"
        pairs.append((query, passage))

    # Score all pairs in one batch (fast on GPU)
    scores = reranker.predict(pairs, show_progress_bar=False)

    # Attach scores and sort
    for doc, score in zip(documents, scores):
        doc["rerank_score"] = float(score)

    documents.sort(key=lambda d: d["rerank_score"], reverse=True)

    if top_k:
        documents = documents[:top_k]

    return documents
