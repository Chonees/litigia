"""Import the JSONL files collected before the catalog existed.

- PJN: text is re-cleaned; fecha and firmantes come from the PDF signatures and the
  tribunal from the page header. The old expediente/carátula are dropped: the old
  parser could pair a PDF with its neighbour's metadata. Re-listing with
  scripts.scrapers.pjn_tribunales fills them in without downloading PDFs again.
- CSJN: metadata was parsed correctly; duplicates collapse on UNIQUE(source, source_id).

Usage (from backend/):
    python -m scripts.import_legacy            # pjn + csjn
    python -m scripts.import_legacy --source pjn
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import quality
from scripts.catalog import Catalog
from scripts.config import settings

FILES = {"pjn": "pjn_tribunales.jsonl", "csjn": "csjn.jsonl"}
EXPEDIENTE = re.compile(r"^\s*([A-Z]{2,5}\s+\d{3,}/\d{4}[^\s]*)", re.MULTILINE)


def from_pjn(row: dict) -> dict:
    raw = row.get("texto") or ""
    firmantes, fecha = quality.extract_firmantes(raw)
    return {
        "source": "pjn",
        "source_id": row["source_id"],
        "texto": quality.clean_pjn_text(raw),
        "tribunal": quality.extract_tribunal(raw),
        "fecha": fecha,
        "firmantes": firmantes,
        "jurisdiccion": row.get("jurisdiccion", ""),
        "caratula": "",
        "expediente": "",
    }


def from_csjn(row: dict) -> dict:
    raw = row.get("texto") or ""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", row.get("fecha") or "")
    exp = EXPEDIENTE.search(raw[:500])
    return {
        "source": "csjn",
        "source_id": row["source_id"],
        "texto": quality.clean_pjn_text(raw),
        "tribunal": row.get("tribunal", ""),
        "fecha": f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "",
        "caratula": row.get("caratula", ""),
        "expediente": exp.group(1) if exp else "",
        "jurisdiccion": row.get("jurisdiccion", ""),
    }


CONVERTERS = {"pjn": from_pjn, "csjn": from_csjn}


def import_file(cat: Catalog, source: str) -> Counter:
    path = settings.data_clean / FILES[source]
    counts: Counter = Counter()
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                counts["corrupt_line"] += 1
                continue
            if cat.has(source, row["source_id"]):
                counts["repeated_id"] += 1
                continue
            counts[cat.upsert(CONVERTERS[source](row), commit=False)] += 1
            if n % 2000 == 0:
                cat.db.commit()
                print(f"  {source}: {n:,} lines {dict(counts)}", flush=True)
    cat.db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy JSONL into the catalog")
    parser.add_argument("--source", choices=list(FILES))
    args = parser.parse_args()

    cat = Catalog(settings.data_root / "catalog.db")
    try:
        for source in [args.source] if args.source else list(FILES):
            print(f"{source}: {dict(import_file(cat, source))}", flush=True)
    finally:
        cat.close()
    print("Next: python -m scripts.audit")


if __name__ == "__main__":
    main()
