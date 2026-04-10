"""Build a SQLite store with full document text for reader enrichment.

ChromaDB stores chunks (4000 chars) for vector search, but readers need
the COMPLETE fallo text to classify correctly. This table maps doc_id -> full text.

Usage:
    python -m scripts.build_fulltext_store
    python -m scripts.build_fulltext_store --status
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def get_db_path() -> Path:
    return settings.data_root / "fulltext_store.db"


def build() -> int:
    db_path = get_db_path()
    print(f"Building fulltext store at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("DROP TABLE IF EXISTS documents")
    conn.execute("""
        CREATE TABLE documents (
            doc_id TEXT PRIMARY KEY,
            texto TEXT NOT NULL,
            caratula TEXT,
            tribunal TEXT,
            fecha TEXT,
            materia TEXT,
            sumario TEXT
        )
    """)

    count = 0
    start = time.time()

    for jsonl_file in sorted(settings.data_clean.glob("*.jsonl")):
        print(f"  Reading {jsonl_file.name}...", flush=True)
        batch = []

        with open(jsonl_file, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] != "{":
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue

                doc_id = d.get("id", "")
                texto = d.get("texto", "")
                if not doc_id or not texto:
                    continue

                batch.append((
                    doc_id,
                    texto,
                    d.get("caratula", ""),
                    d.get("tribunal", ""),
                    d.get("fecha", ""),
                    d.get("materia", ""),
                    d.get("sumario", ""),
                ))
                count += 1

                if len(batch) >= 5000:
                    conn.executemany(
                        "INSERT OR IGNORE INTO documents(doc_id, texto, caratula, tribunal, fecha, materia, sumario) VALUES (?,?,?,?,?,?,?)",
                        batch,
                    )
                    conn.commit()
                    batch = []
                    elapsed = time.time() - start
                    print(f"    {count:,} documents stored ({elapsed:.0f}s)", flush=True)

        if batch:
            conn.executemany(
                "INSERT OR IGNORE INTO documents(doc_id, texto, caratula, tribunal, fecha, materia, sumario) VALUES (?,?,?,?,?,?,?)",
                batch,
            )
            conn.commit()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON documents(doc_id)")
    conn.close()

    elapsed = time.time() - start
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"\n  Fulltext store built: {count:,} documents, {db_size_mb:.0f}MB, {elapsed:.0f}s")
    return count


def status():
    db_path = get_db_path()
    if not db_path.exists():
        print(f"Fulltext store not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"Fulltext store: {row[0]:,} documents, {db_size_mb:.0f}MB at {db_path}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LITIGIA Fulltext Store Builder")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        status()
    else:
        build()
