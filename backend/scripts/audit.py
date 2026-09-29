"""Audit the catalog against the data contract and track it over time.

Each run prints the report, saves a snapshot to $DATA_ROOT/logs/audits/, and
compares with the previous snapshot so you can see if a scraper change helped.

Usage (from backend/):
    python -m scripts.audit
    python -m scripts.audit --reassess     # re-apply the current contract first
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import quality
from scripts.catalog import Catalog
from scripts.config import settings


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def summarize(cat: Catalog) -> dict:
    out: dict = {}
    sources = [r[0] for r in cat.db.execute("SELECT DISTINCT source FROM documents ORDER BY source")]
    for source in sources:
        status: Counter = Counter()
        reasons: Counter = Counter()
        warnings: Counter = Counter()
        by_fuero_year: dict = defaultdict(Counter)
        rows = cat.db.execute(
            "SELECT status, reasons, warnings, fuero, substr(fecha, 1, 4) AS year FROM documents "
            "WHERE source=? AND active=1",
            (source,),
        )
        for row in rows:
            status[row["status"]] += 1
            for r in json.loads(row["reasons"]):
                reasons[r.split(":")[0]] += 1
            warnings.update(json.loads(row["warnings"]))
            if row["status"] == "indexable":
                by_fuero_year[row["fuero"] or "?"][row["year"] or "?"] += 1

        documents = sum(status.values())
        disabled = cat.db.execute(
            "SELECT COUNT(*) FROM documents WHERE source=? AND active=0", (source,)
        ).fetchone()[0]
        leaves = cat.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0), COALESCE(SUM(fetched), 0), COALESCE(SUM(truncated), 0) "
            "FROM searches WHERE source=? AND split=0",
            (source,),
        ).fetchone()
        out[source] = {
            "documents": documents,
            "disabled": disabled,
            "status": dict(status),
            "indexable_pct": _pct(status["indexable"], documents),
            "reasons": dict(reasons.most_common()),
            "warnings": dict(warnings.most_common()),
            "by_fuero_year": {f: dict(sorted(y.items())) for f, y in sorted(by_fuero_year.items())},
            "searches": {
                "leaves": leaves[0],
                "reported": leaves[1],
                "fetched": leaves[2],
                "completeness_pct": _pct(leaves[2], leaves[1]),
                "truncated": leaves[3],
            },
        }
    return out


def compare(before: dict, after: dict) -> dict:
    delta = {}
    for source, now in after.items():
        prev = before.get(source, {})
        delta[source] = {
            "documents": now["documents"] - prev.get("documents", 0),
            "indexable": now["status"].get("indexable", 0) - prev.get("status", {}).get("indexable", 0),
            "indexable_pct": round(now["indexable_pct"] - prev.get("indexable_pct", 0.0), 1),
        }
    return delta


def _print(summary: dict, delta: dict | None) -> None:
    print(f"\nContrato: {json.dumps(quality.CONTRACT, ensure_ascii=False)}")
    for source, s in summary.items():
        off = f" ({s['disabled']:,} deshabilitados, no cuentan)" if s.get("disabled") else ""
        print(f"\n{'=' * 64}\n{source.upper()}: {s['documents']:,} documentos activos{off}")
        print(f"  Indexables: {s['status'].get('indexable', 0):,} ({s['indexable_pct']}%)")
        for st, n in sorted(s["status"].items(), key=lambda x: -x[1]):
            print(f"    {st:<10} {n:>8,}  {_pct(n, s['documents']):>5}%")
        if delta and source in delta:
            d = delta[source]
            print(f"  Desde la auditoría anterior: {d['documents']:+,} docs, "
                  f"{d['indexable']:+,} indexables, {d['indexable_pct']:+.1f} pp")
        if s["reasons"]:
            print("  Motivos (rechazo / pendiente):")
            for r, n in s["reasons"].items():
                print(f"    {r:<22} {n:>8,}  {_pct(n, s['documents']):>5}%")
        if s["warnings"]:
            print("  Advertencias:")
            for w, n in s["warnings"].items():
                print(f"    {w:<22} {n:>8,}  {_pct(n, s['documents']):>5}%")
        sr = s["searches"]
        if sr["leaves"]:
            print(f"  Completitud contra el sitio: {sr['fetched']:,} de {sr['reported']:,} "
                  f"({sr['completeness_pct']}%) en {sr['leaves']:,} búsquedas; truncadas: {sr['truncated']:,}")
        if s["by_fuero_year"]:
            print("  Indexables por fuero:")
            for fuero, years in s["by_fuero_year"].items():
                total = sum(years.values())
                span = f"{min(years)}–{max(years)}" if years else ""
                print(f"    {fuero:<34} {total:>7,}  ({span})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the LITIGIA catalog")
    parser.add_argument("--reassess", action="store_true", help="Re-apply the current contract before auditing")
    args = parser.parse_args()

    cat = Catalog(settings.data_root / "catalog.db")
    if args.reassess:
        print(f"Reassessing: {cat.reassess()}")
    summary = summarize(cat)
    cat.close()

    audits = settings.data_logs / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    previous = sorted(audits.glob("audit_*.json"))
    delta = compare(json.loads(previous[-1].read_text(encoding="utf-8"))["summary"], summary) if previous else None

    _print(summary, delta)
    snapshot = audits / f"audit_{time.strftime('%Y%m%d_%H%M%S')}.json"
    snapshot.write_text(
        json.dumps({"contract": quality.CONTRACT, "summary": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"\nSnapshot: {snapshot}")


if __name__ == "__main__":
    main()
