"""Hybrid search pipeline: Vector + FTS5 + BM25 + Cross-encoder rerank.

Includes relevance threshold filtering to prevent analyzing irrelevant results.
"""

import re as _re
from datetime import datetime

from app.core.config import settings
from app.services.embeddings import get_query_embedding
from app.services.keyword_search import keyword_search
from app.services.reranker import rerank
from app.services.vector_store import search_similar, get_collection

from app.services.analysis_helpers import clean_markup


def _bm25_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    """BM25 keyword search over pre-fetched results. Catches exact legal terms."""
    from rank_bm25 import BM25Okapi

    if not results:
        return results

    # Tokenize: simple whitespace + lowercase for Spanish legal text
    query_tokens = query.lower().split()
    corpus = []
    for r in results:
        text = f"{r.get('caratula', '')} {r.get('sumario', '')} {r.get('texto', '')[:1000]}"
        corpus.append(text.lower().split())

    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(query_tokens)

    for r, score in zip(results, bm25_scores):
        r["bm25_score"] = float(score)

    return results


def _rrf_fusion(results: list[dict], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion — merges vector + BM25 rankings."""
    # Rank by vector score
    by_vector = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
    # Rank by BM25 score
    by_bm25 = sorted(results, key=lambda r: r.get("bm25_score", 0), reverse=True)

    rrf_scores: dict[str, float] = {}
    id_map: dict[str, dict] = {}

    for ranking in [by_vector, by_bm25]:
        for rank, doc in enumerate(ranking, 1):
            doc_id = doc.get("id", str(id(doc)))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)
            id_map[doc_id] = doc

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    for doc_id in sorted_ids:
        id_map[doc_id]["rrf_score"] = rrf_scores[doc_id]

    return [id_map[doc_id] for doc_id in sorted_ids]


async def search_cases(caso: str, fuero: str | None, top_k: int = 100) -> list[dict]:
    """Hybrid search: Vector + Global FTS5 keywords -> merge -> cross-encoder rerank.

    Includes relevance threshold: results below settings.rerank_min_score are dropped.
    Returns empty list if fewer than settings.rerank_min_results pass the threshold.
    """
    search_text = caso
    if fuero:
        search_text += f" fuero {fuero}"

    embedding = await get_query_embedding(search_text)

    # --- Source 1: Vector search ---
    fetch_k = min(top_k * 3, 500)
    vector_results = await search_similar(query_embedding=embedding, top_k=fetch_k, fuero=fuero)
    if not vector_results and fuero:
        vector_results = await search_similar(query_embedding=embedding, top_k=fetch_k)
    print(f"  [Vector] {len(vector_results)} results", flush=True)

    # --- Source 2: Global FTS5 keyword search ---
    fts_ids = []
    try:
        fts_ids = keyword_search(caso, top_k=fetch_k)
        print(f"  [FTS5] {len(fts_ids)} keyword matches", flush=True)
    except Exception as e:
        print(f"  [FTS5] Skipped: {e}", flush=True)

    # Fetch FTS results from ChromaDB by ID
    fts_results = []
    if fts_ids:
        # Deduplicate FTS IDs before fetching from ChromaDB
        fts_ids = list(dict.fromkeys(fts_ids))[:100]
        collection = get_collection()
        try:
            fts_data = collection.get(ids=fts_ids, include=["documents", "metadatas"])
            for i, doc_id in enumerate(fts_data["ids"]):
                meta = fts_data["metadatas"][i] if fts_data["metadatas"] else {}
                fts_results.append({
                    "id": doc_id,
                    "score": 0.85,  # synthetic score for fusion
                    "texto": fts_data["documents"][i] if fts_data["documents"] else "",
                    **meta,
                })
        except Exception as e:
            print(f"  [FTS5>ChromaDB] Error fetching: {str(e).encode('ascii', 'replace').decode()}", flush=True)

    # --- Merge: combine both sources, dedup by ID ---
    seen_ids: set[str] = set()
    merged = []
    for r in vector_results:
        rid = r.get("id", "")
        if rid not in seen_ids:
            seen_ids.add(rid)
            r["_source"] = "vector"
            merged.append(r)
    fts_added = 0
    for r in fts_results:
        rid = r.get("id", "")
        if rid not in seen_ids:
            seen_ids.add(rid)
            r["_source"] = "fts"
            merged.append(r)
            fts_added += 1
    if fts_added:
        print(f"  [Merge] Added {fts_added} FTS-only results (not in vector top-{fetch_k})", flush=True)

    # Clean markup
    for r in merged:
        for key in ("texto", "sumario", "caratula"):
            if r.get(key):
                r[key] = clean_markup(r[key])

    # --- Dedup by caratula ---
    seen_caratulas: set[str] = set()
    deduped = []
    for r in merged:
        key = r.get("caratula", "")[:60].lower().strip()
        if key and key in seen_caratulas:
            continue
        if key:
            seen_caratulas.add(key)
        deduped.append(r)
    if len(deduped) < len(merged):
        print(f"  [Dedup] {len(merged)} -> {len(deduped)}", flush=True)

    # --- Cross-encoder rerank for final precision ---
    if deduped:
        rerank_k = min(len(deduped), max(top_k * 2, 100), 200)
        print(f"  [Reranker] Scoring {rerank_k} candidates with bge-reranker-v2-m3...", flush=True)
        ranked = rerank(caso, deduped[:rerank_k], top_k=None)

        # --- Relevance threshold: drop semantically irrelevant results ---
        min_score = settings.rerank_min_score
        if min_score is not None and ranked:
            before = len(ranked)
            ranked = [r for r in ranked if r.get("rerank_score", 0) >= min_score]
            dropped = before - len(ranked)
            if dropped:
                print(
                    f"  [Relevance] {dropped}/{before} dropped "
                    f"(rerank_score < {min_score}). "
                    f"{len(ranked)} remain.",
                    flush=True,
                )
            if len(ranked) < settings.rerank_min_results:
                print(
                    f"  [Relevance] Only {len(ranked)} results above threshold "
                    f"(need {settings.rerank_min_results}). No relevant results.",
                    flush=True,
                )
                return []

        # --- Recency boost: newer fallos get a score bump ---
        # A 2026 fallo with rerank 0.80 beats a 2005 fallo with rerank 0.82
        # But a 2005 fallo with rerank 0.95 still beats a 2026 fallo with 0.80
        current_year = datetime.now().year
        for r in ranked:
            fecha = r.get("fecha", "")
            year = None
            # Try to extract year from various date formats
            m = _re.search(r"(\d{4})", fecha)
            if m:
                year = int(m.group(1))
            if year and 1900 < year <= current_year:
                years_ago = current_year - year
                # Boost: 0.15 for this year, decaying to 0 for 30+ years ago
                recency_boost = max(0, 0.15 * (1 - years_ago / 30))
                r["_final_score"] = r.get("rerank_score", 0) + recency_boost
            else:
                r["_final_score"] = r.get("rerank_score", 0)

        ranked.sort(key=lambda r: r["_final_score"], reverse=True)
        newest = next((r for r in ranked if r.get("fecha")), None)
        if newest:
            print(f"  [Recency] Applied boost. Top result year: {newest.get('fecha','?')}", flush=True)

        # --- Diversity: cap per tribunal, but backfill if not enough ---
        MAX_PER_TRIBUNAL = max(5, top_k // 3)
        tribunal_counts: dict[str, int] = {}
        results = []
        skipped = []
        for r in ranked:
            tribunal = (r.get("tribunal", "") or "").strip()
            if not tribunal:
                results.append(r)
            else:
                count = tribunal_counts.get(tribunal, 0)
                if count < MAX_PER_TRIBUNAL:
                    results.append(r)
                    tribunal_counts[tribunal] = count + 1
                else:
                    skipped.append(r)
            if len(results) >= top_k:
                break

        # Backfill: if diversity filter left us short, add back skipped by rerank score
        if len(results) < top_k and skipped:
            need = top_k - len(results)
            results.extend(skipped[:need])

        print(f"  [Final] {len(results)} results (diversity cap {MAX_PER_TRIBUNAL}/tribunal). Best rerank: {results[0].get('rerank_score', 0):.3f}", flush=True)
        return results

    return deduped[:top_k]
