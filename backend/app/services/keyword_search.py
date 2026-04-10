"""Global BM25 keyword search using SQLite FTS5.

Builds a full-text index over all documents for exact keyword matching.
Catches legal terms that vector search misses (art. 31, tercerización, etc.)
Zero dependencies — SQLite is built into Python.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.core.config import settings

_DB_PATH: Path | None = None
_conn: sqlite3.Connection | None = None


def _get_db_path() -> Path:
    return settings.data_root / "fts_index.db"


def _get_conn() -> sqlite3.Connection | None:
    global _conn
    if _conn is None:
        db_path = _get_db_path()
        if not db_path.exists():
            print(f"WARNING: FTS index not found at {db_path}. Keyword search disabled.", flush=True)
            return None
        _conn = sqlite3.connect(str(db_path))
        _conn.row_factory = sqlite3.Row
    return _conn


def keyword_search(query: str, top_k: int = 50) -> list[str]:
    """Search FTS5 index, return matching document IDs ranked by BM25.

    Returns list of doc_ids that can be used to fetch from ChromaDB.
    Returns [] if FTS index is not available.
    """
    conn = _get_conn()
    if conn is None:
        return []
    # FTS5 match query — wrap each word in quotes to handle special chars
    tokens = query.strip().split()
    fts_query = " OR ".join(f'"{t}"' for t in tokens if len(t) > 2)

    if not fts_query:
        return []

    try:
        cursor = conn.execute(
            """SELECT doc_id, rank FROM fts_docs WHERE fts_docs MATCH ? ORDER BY rank LIMIT ?""",
            (fts_query, top_k),
        )
        return [row["doc_id"] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


def build_index() -> int:
    """Build the FTS5 index from all JSONL files. Run once."""
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path))

    conn.execute("DROP TABLE IF EXISTS fts_docs")
    conn.execute("""
        CREATE VIRTUAL TABLE fts_docs USING fts5(
            doc_id,
            caratula,
            texto,
            tribunal,
            materia
        )
    """)

    count = 0
    clean_dir = settings.data_clean
    for jsonl_file in clean_dir.glob("*.jsonl"):
        print(f"  Indexing {jsonl_file.name}...", flush=True)
        with open(jsonl_file, "r", encoding="utf-8-sig") as f:
            batch = []
            for line in f:
                line = line.strip()
                if not line or line[0] != "{":
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue

                batch.append((
                    d.get("id", ""),
                    d.get("caratula", ""),
                    (d.get("texto", "") + " " + d.get("sumario", ""))[:2000],
                    d.get("tribunal", ""),
                    d.get("materia", ""),
                ))
                count += 1

                if len(batch) >= 5000:
                    conn.executemany(
                        "INSERT INTO fts_docs(doc_id, caratula, texto, tribunal, materia) VALUES (?,?,?,?,?)",
                        batch,
                    )
                    conn.commit()
                    batch = []
                    print(f"    {count:,} indexed...", flush=True)

            if batch:
                conn.executemany(
                    "INSERT INTO fts_docs(doc_id, caratula, texto, tribunal, materia) VALUES (?,?,?,?,?)",
                    batch,
                )
                conn.commit()

    conn.close()
    print(f"  FTS index built: {count:,} documents at {db_path}", flush=True)
    return count
