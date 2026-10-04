"""SQLite catalog: the single store for every collected fallo and every search.

- UNIQUE(source, source_id) makes duplicate rows impossible.
- Identical text under another id is kept but labelled `duplicate`.
- Each row carries the quality verdict (status + reasons) from scripts.quality
  and the enrichment fields from scripts.enrich.
- `searches` records what the site reported, so the audit can measure completeness.
- `listings` records which rulings each search listed, and `failures` which PDFs could not be read
  (with the reason), so every ruling the site reported can be accounted for (scripts/reconcile.py).
- WAL mode: readers (audit) never block writers (scrapers).
- `disable()` hides rows without deleting them; a fresh scrape of the same fallo re-enables it.
"""

import hashlib
import json
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

from scripts import quality
from scripts.enrich import detect_instancia, enrich

META_FIELDS = ["url", "tribunal", "jurisdiccion", "fecha", "caratula", "expediente", "tipo_fallo"]

# Every column after the identity ones. New columns are added to existing catalogs on open.
COLUMNS = {
    "url": "TEXT DEFAULT ''",
    "texto": "TEXT DEFAULT ''",
    "chars": "INTEGER DEFAULT 0",
    "text_hash": "TEXT DEFAULT ''",
    "tribunal": "TEXT DEFAULT ''",
    "sala": "TEXT DEFAULT ''",
    "fuero": "TEXT DEFAULT ''",
    "instancia": "TEXT DEFAULT ''",
    "jurisdiccion": "TEXT DEFAULT ''",
    "fecha": "TEXT DEFAULT ''",
    "caratula": "TEXT DEFAULT ''",
    "expediente": "TEXT DEFAULT ''",
    "tipo_fallo": "TEXT DEFAULT ''",
    "firmantes": "TEXT DEFAULT '[]'",
    # enrichment (scripts/enrich.py)
    "objeto": "TEXT DEFAULT ''",
    "resultado": "TEXT DEFAULT ''",
    "normas": "TEXT DEFAULT '[]'",
    "numero": "TEXT DEFAULT ''",
    "expediente_texto": "TEXT DEFAULT ''",
    "votos": "TEXT DEFAULT '[]'",
    "por_mayoria": "INTEGER DEFAULT 0",
    # data contract (scripts/quality.py)
    "status": "TEXT DEFAULT ''",
    "reasons": "TEXT DEFAULT '[]'",
    "warnings": "TEXT DEFAULT '[]'",
    # disabled rows stay in the catalog but are ignored by the audit and the search index
    "active": "INTEGER DEFAULT 1",
    "disabled_reason": "TEXT DEFAULT ''",
    "first_seen": "TEXT",
    "updated_at": "TEXT",
}
MANAGED = ("active", "disabled_reason", "first_seen", "updated_at")   # not written by _save
JSON_COLUMNS = ("firmantes", "normas", "votos", "reasons", "warnings")

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id        TEXT PRIMARY KEY,
    source    TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS searches (
    source     TEXT NOT NULL,
    key        TEXT NOT NULL,
    total      INTEGER,
    fetched    INTEGER,
    split      INTEGER,
    truncated  INTEGER,
    at         TEXT,
    PRIMARY KEY (source, key)
);
CREATE TABLE IF NOT EXISTS listings (
    source     TEXT NOT NULL,
    key        TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    PRIMARY KEY (source, key, source_id)
);
CREATE TABLE IF NOT EXISTS failures (
    source     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    url        TEXT,
    key        TEXT,
    reason     TEXT,
    attempts   INTEGER DEFAULT 1,
    first_at   TEXT,
    last_at    TEXT,
    PRIMARY KEY (source, source_id)
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(text_hash);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(source, status);
"""

SALA = re.compile(r"\bSALA\s+(FERIA|[IVX]+|[A-Z]|\d+)\b", re.IGNORECASE)


def doc_id(source: str, source_id: str) -> str:
    return hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Catalog:
    def __init__(self, path: Path, busy_timeout: float = 120.0):
        # 120 s: a batch reassess holds the write lock while it re-runs the rules on long rulings; a scraper
        # writing at the same time waited only 30 s and died with "database is locked" (2026-09-30).
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=busy_timeout)
        # WAL: the audit can read the whole catalog while a scraper keeps writing.
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._migrate()
        self.db.executescript(INDEXES)

    def _migrate(self) -> None:
        existing = {r[1] for r in self.db.execute("PRAGMA table_info(documents)")}
        for name, decl in COLUMNS.items():
            if name not in existing:
                self.db.execute(f"ALTER TABLE documents ADD COLUMN {name} {decl}")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # -- documents ----------------------------------------------------------

    def has(self, source: str, source_id: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM documents WHERE source=? AND source_id=?", (source, source_id)
        ).fetchone() is not None

    def get(self, source: str, source_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM documents WHERE source=? AND source_id=?", (source, source_id)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in JSON_COLUMNS:
            d[key] = json.loads(d[key] or "[]")
        return d

    def count(self, active_only: bool = False) -> int:
        where = " WHERE active=1" if active_only else ""
        return self.db.execute(f"SELECT COUNT(*) FROM documents{where}").fetchone()[0]

    def disable(self, where: str, params: tuple = (), *, reason: str) -> int:
        """Hide documents from audit and search without deleting them. Returns how many."""
        n = self.db.execute(
            f"UPDATE documents SET active=0, disabled_reason=? WHERE active=1 AND ({where})", (reason, *params)
        ).rowcount
        self.db.commit()
        return n

    def enable(self, where: str, params: tuple = ()) -> int:
        n = self.db.execute(
            f"UPDATE documents SET active=1, disabled_reason='' WHERE active=0 AND ({where})", params
        ).rowcount
        self.db.commit()
        return n

    def upsert(self, doc: dict, commit: bool = True) -> str:
        """Insert or merge a document; non-empty new values win, empty ones never erase."""
        source, source_id = doc["source"], doc["source_id"]
        merged = self.get(source, source_id) or {"firmantes": []}
        for key in META_FIELDS + ["texto"]:
            if doc.get(key):
                merged[key] = doc[key]
        if doc.get("firmantes"):
            merged["firmantes"] = doc["firmantes"]
        merged.update(source=source, source_id=source_id, id=doc_id(source, source_id))
        self._save(merged)
        # A fresh scrape of a disabled document brings it back.
        self.db.execute("UPDATE documents SET active=1, disabled_reason='' WHERE id=? AND active=0", (merged["id"],))
        if commit:
            self.db.commit()
        return merged["status"]

    def _save(self, d: dict) -> None:
        texto = quality.strip_noise_paragraphs(d.get("texto") or "")
        tribunal = d.get("tribunal") or ""
        sala = SALA.search(tribunal)
        d.update(
            texto=texto,
            tribunal=tribunal,
            chars=len(texto),
            text_hash=quality.text_hash(texto) if texto else "",
            fuero=quality.detect_fuero(tribunal),
            instancia=detect_instancia(tribunal),
            sala=sala.group(1).upper() if sala else "",
            **enrich({"texto": texto, "caratula": d.get("caratula") or ""}),
        )
        verdict = quality.assess(d)
        d.update(status=verdict.status, reasons=verdict.reasons, warnings=verdict.warnings)

        original = self._original_for(d["text_hash"], d["id"])
        if original:
            d.update(status="duplicate", reasons=[f"duplicado_de:{original}"])

        stored = [c for c in COLUMNS if c not in MANAGED]
        values = {c: d.get(c) for c in stored}
        for c in JSON_COLUMNS:
            values[c] = json.dumps(d.get(c) or [], ensure_ascii=False)
        for c in stored:
            if values[c] is None:
                values[c] = 0 if COLUMNS[c].startswith("INTEGER") else ""
        values["por_mayoria"] = int(bool(d.get("por_mayoria")))
        cols = ["id", "source", "source_id"] + stored
        self.db.execute(
            f"INSERT INTO documents ({', '.join(cols)}, first_seen, updated_at) "
            f"VALUES ({', '.join(':' + c for c in cols)}, :now, :now) "
            f"ON CONFLICT(id) DO UPDATE SET "
            + ", ".join(f"{c}=excluded.{c}" for c in stored + ["updated_at"]),
            {**values, "id": d["id"], "source": d["source"], "source_id": d["source_id"], "now": _now()},
        )

    def _original_for(self, text_hash: str, own_id: str) -> str | None:
        if not text_hash:
            return None
        row = self.db.execute(
            "SELECT id FROM documents WHERE text_hash=? AND id<>? AND status<>'duplicate' "
            "ORDER BY first_seen, id LIMIT 1",
            (text_hash, own_id),
        ).fetchone()
        return row["id"] if row else None

    def reassess(self, source: str | None = None, commit_every: int = 500, active_only: bool = True) -> dict:
        """Apply the current contract to what is stored: the active documents, or all with active_only=False.

        Disabled documents (the old scraper's) are not searched, so their fields are not recomputed; one that
        is enabled again is active by the next run. Commits in batches: readers (agents, audits) keep a
        consistent view meanwhile, and an interrupted run keeps what it finished.
        """
        conditions = (["source=?"] if source else []) + (["active=1"] if active_only else [])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params = (source,) if source else ()
        ids = [r["id"] for r in self.db.execute(f"SELECT id FROM documents {where} ORDER BY first_seen, id", params)]
        counts: Counter = Counter()
        for n, id_ in enumerate(ids, 1):
            row = dict(self.db.execute("SELECT * FROM documents WHERE id=?", (id_,)).fetchone())
            row["firmantes"] = json.loads(row["firmantes"] or "[]")
            self._save(row)
            counts[row["status"]] += 1
            if n % commit_every == 0:
                self.db.commit()
        self.db.commit()
        return dict(counts)

    def merge_from(self, other_path: Path) -> dict:
        """Bring every document and search from another catalog (e.g. a VPS's) into this one.

        Documents go through `upsert`, so the current contract and enrichment are re-applied
        and existing rows are merged, never duplicated. Idempotent.
        """
        other = sqlite3.connect(f"file:{other_path}?mode=ro", uri=True)
        other.row_factory = sqlite3.Row
        docs = 0
        for row in other.execute("SELECT * FROM documents"):
            d = dict(row)
            d["firmantes"] = json.loads(d.get("firmantes") or "[]")
            self.upsert({k: d.get(k) for k in ["source", "source_id", "texto", "firmantes", *META_FIELDS]}, commit=False)
            docs += 1
        searches = 0
        for row in other.execute("SELECT source, key, total, fetched, split, truncated, at FROM searches"):
            self.db.execute("INSERT OR REPLACE INTO searches VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(row))
            searches += 1
        self.db.commit()
        other.close()
        return {"documents": docs, "searches": searches}

    # -- searches -----------------------------------------------------------

    def record_search(self, source: str, key: str, *, total: int, fetched: int, split: bool, truncated: bool) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO searches VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source, key, total, fetched, int(split), int(truncated), _now()),
        )
        self.db.commit()

    def search_done(self, source: str, key: str) -> bool:
        """Fully collected: not split, and not truncated (a truncated day still needs its oficina split)."""
        return self.db.execute(
            "SELECT 1 FROM searches WHERE source=? AND key=? AND split=0 AND truncated=0", (source, key)
        ).fetchone() is not None

    # -- accounting ---------------------------------------------------------

    def record_listing(self, source: str, key: str, source_ids: list[str]) -> None:
        """The rulings one search listed (idempotent: a re-run lists them again)."""
        self.db.executemany("INSERT OR IGNORE INTO listings VALUES (?, ?, ?)", [(source, key, i) for i in source_ids])
        self.db.commit()

    def record_failure(self, source: str, source_id: str, *, url: str, key: str, reason: str) -> None:
        now = _now()
        self.db.execute(
            "INSERT INTO failures VALUES (?, ?, ?, ?, ?, 1, ?, ?) ON CONFLICT(source, source_id) DO UPDATE SET "
            "attempts=attempts+1, reason=excluded.reason, url=excluded.url, key=excluded.key, last_at=excluded.last_at",
            (source, source_id, url, key, reason, now, now),
        )
        self.db.commit()

    def clear_failure(self, source: str, source_id: str) -> None:
        self.db.execute("DELETE FROM failures WHERE source=? AND source_id=?", (source, source_id))
        self.db.commit()

    def search_total(self, source: str, key: str) -> int:
        """What the site reported for a search already made; 0 if never searched."""
        row = self.db.execute("SELECT total FROM searches WHERE source=? AND key=?", (source, key)).fetchone()
        return row["total"] if row and row["total"] else 0
