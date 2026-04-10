"""Fulltext document store — maps doc_id to complete fallo text.

ChromaDB stores chunks for vector search. This SQLite table stores the
COMPLETE text so readers can analyze the full fallo, not just a chunk.

Usage in pipeline:
    from app.services.fulltext_store import enrich_with_fulltext
    results = enrich_with_fulltext(results)  # replaces chunk text with full text
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.core.config import settings

_conn: sqlite3.Connection | None = None


def _get_db_path() -> Path:
    return settings.data_root / "fulltext_store.db"


def _get_conn() -> sqlite3.Connection | None:
    global _conn
    if _conn is None:
        db_path = _get_db_path()
        if not db_path.exists():
            print(f"WARNING: Fulltext store not found at {db_path}. Readers will use chunk text.", flush=True)
            return None
        _conn = sqlite3.connect(str(db_path))
        _conn.row_factory = sqlite3.Row
    return _conn


# Chunk ID pattern: {original_id}_c{N}
_CHUNK_RE = re.compile(r"^(.+)_c\d+$")


def _get_original_id(chunk_id: str) -> str:
    """Strip chunk suffix to get the original document ID."""
    m = _CHUNK_RE.match(chunk_id)
    return m.group(1) if m else chunk_id


def get_fulltext(doc_id: str) -> str | None:
    """Look up full document text by ID. Returns None if not found."""
    conn = _get_conn()
    if conn is None:
        return None

    original_id = _get_original_id(doc_id)
    row = conn.execute(
        "SELECT texto FROM documents WHERE doc_id = ?", (original_id,)
    ).fetchone()
    return row["texto"] if row else None


def enrich_with_fulltext(results: list[dict]) -> list[dict]:
    """Replace chunk text with full document text for each search result.

    If fulltext store is not available, returns results unchanged.
    If a doc_id is not found, keeps the original chunk text.
    """
    conn = _get_conn()
    if conn is None:
        return results

    enriched = 0
    for r in results:
        doc_id = r.get("id", "")
        if not doc_id:
            continue

        original_id = _get_original_id(doc_id)
        row = conn.execute(
            "SELECT texto FROM documents WHERE doc_id = ?", (original_id,)
        ).fetchone()

        if row and row["texto"]:
            chunk_len = len(r.get("texto", ""))
            full_len = len(row["texto"])
            if full_len > chunk_len:
                r["texto"] = row["texto"]
                enriched += 1

    if enriched:
        print(f"  [Fulltext] Enriched {enriched}/{len(results)} results with complete text", flush=True)

    return results
