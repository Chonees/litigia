"""Find a ruling cited by an external source (news, bulletin, commentary) in the catalog.

Search by words of the carátula (party names), optionally narrowed by date, fuero and Sala. Prints
candidates with what is needed to confirm the match: date, court, carátula, case number and the start
of the resolutive part. Read-only.

Usage (from backend/):
  python -m spikes.find_ruling "GONZALEZ ARAGON" "ASOCIART" [--desde 2026-03-01 --hasta 2026-03-31]
                               [--fuero laboral] [--sala VI] [--expediente 49971/2016]
"""

import argparse
import re
import sqlite3
import unicodedata

from scripts.config import settings
from scripts.enrich import _resolutive


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("words", nargs="*", help="words that must appear in the carátula (accents and case ignored)")
    p.add_argument("--desde")
    p.add_argument("--hasta")
    p.add_argument("--fuero")
    p.add_argument("--sala")
    p.add_argument("--expediente", help="number/year, e.g. 49971/2016")
    p.add_argument("--max", type=int, default=8)
    a = p.parse_args()
    if not a.words and not a.expediente:
        p.error("give carátula words or --expediente")
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    where, params = ["source='pjn'", "active=1"], []
    if a.desde:
        where.append("fecha >= ?"); params.append(a.desde)
    if a.hasta:
        where.append("fecha <= ?"); params.append(a.hasta)
    if a.fuero:
        where.append("fuero = ?"); params.append(a.fuero)
    if a.sala:
        where.append("sala = ?"); params.append(a.sala.upper())
    for w in a.words:
        where.append("caratula LIKE ?"); params.append(f"%{w}%")
    if a.expediente:
        num, _, year = a.expediente.partition("/")
        where.append("(expediente LIKE ? OR expediente_texto = ?)")
        params += [f"%{int(num):06d}/{year}%", f"{int(num)}/{year}"]
    rows = db.execute(f"SELECT id, fecha, tribunal, sala, caratula, expediente, status, texto FROM documents "
                      f"WHERE {' AND '.join(where)} ORDER BY fecha LIMIT ?", (*params, a.max * 5)).fetchall()
    # SQLite LIKE is accent-sensitive: also accept accent-folded matches done in Python
    words = [fold(w) for w in a.words]
    rows = [r for r in rows if all(w in fold(r["caratula"]) for w in words)][:a.max]
    print(f"{len(rows)} candidato(s)")
    for r in rows:
        sec, _ = _resolutive(r["texto"])
        resol = re.sub(r"\s+", " ", sec[:300]).strip()
        print(f"\n- id {r['id']} · {r['fecha']} · {r['tribunal']} (Sala {r['sala'] or '-'}) · {r['status']}")
        print(f"  {r['caratula']} · expediente {r['expediente']}")
        print(f"  resolutivo: {resol or '(no detectado)'}")


if __name__ == "__main__":
    main()
