"""Live view of the multi-fuero pilot, straight from the catalog's accounting tables.

Per cámara: what the site reported for the range, how many rulings it listed, how many are stored
with text, how many PDFs failed, speed and time left. Refreshes every 10 s; Ctrl+C to stop.
Usage (from backend/): python -m spikes.watch_pilot [--once]
"""

import argparse
import os
import re
import sqlite3
import time
from datetime import datetime

from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO

CAMARAS = ["C_1", "C_10", "C_5", "C_2"]
DESDE, HASTA, LIMIT = "2026-08-01", "2026-09-27", 1000
TS = re.compile(r"^\[(\d\d:\d\d:\d\d)\]")


def snapshot(db: sqlite3.Connection, camara: str) -> dict:
    row = db.execute("SELECT total FROM searches WHERE source='pjn' AND key=?",
                     (f"5-5|{camara}|*|D|{DESDE}|{HASTA}",)).fetchone()
    sitio = row[0] if row else None
    ids = {r[0] for r in db.execute(
        "SELECT source_id FROM listings WHERE source='pjn' AND key LIKE ? AND substr(key, -21, 10) >= ? "
        "AND substr(key, -10) <= ?", (f"5-5|{camara}|%|D|%", DESDE, HASTA))}
    guardados = fallidos = 0
    if ids:
        marks = ",".join("?" * len(ids))
        guardados = db.execute(f"SELECT COUNT(*) FROM documents WHERE source='pjn' AND chars>0 AND source_id IN ({marks})",
                               tuple(ids)).fetchone()[0]
        fallidos = db.execute(f"SELECT COUNT(*) FROM failures WHERE source='pjn' AND source_id IN ({marks})",
                              tuple(ids)).fetchone()[0]
    return {"sitio": sitio, "listados": len(ids), "guardados": guardados, "fallidos": fallidos}


def log_info(camara: str) -> tuple[str, float | None]:
    """Last log line and minutes since the run started (None if it has not started)."""
    path = settings.data_logs / f"pilot_{camara}.log"
    if not path.exists():
        return "", None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    first = next((TS.match(l).group(1) for l in lines if TS.match(l)), None)
    minutes = None
    if first:
        start = datetime.combine(datetime.now().date(), datetime.strptime(first, "%H:%M:%S").time())
        minutes = max((datetime.now() - start).total_seconds() / 60, 0.1)
    return (lines[-1] if lines else ""), minutes


def render(db: sqlite3.Connection) -> str:
    out = [f"Piloto multi-fuero · {DESDE}..{HASTA} · tope {LIMIT} por fuero · {time.strftime('%H:%M:%S')}", ""]
    for c in CAMARAS:
        s = snapshot(db, c)
        last, minutes = log_info(c)
        meta = min(s["sitio"], LIMIT) if s["sitio"] is not None else LIMIT
        hechos = s["guardados"] + s["fallidos"]
        bar = "#" * int(20 * min(hechos / meta, 1)) if meta else ""
        name = f"{c} {CAMARA_FUERO[c]}"
        if minutes is None and not s["listados"]:
            out += [f"{name:<42} pendiente", ""]
            continue
        sitio = "?" if s["sitio"] is None else f"{s['sitio']:,}"
        tope = f" (el piloto corta en {LIMIT:,} nuevos)" if s["sitio"] and s["sitio"] > LIMIT else ""
        out.append(f"{name:<42} [{bar:<20}] {hechos:>5,} de {sitio} en el sitio{tope}")
        eta = ""
        if minutes and hechos and hechos < meta and last and "DONE" not in last:
            rate = hechos / minutes
            eta = f" · {rate:.0f}/min · faltan ~{(meta - hechos) / rate:.0f} min"
        out.append(f"   sitio {sitio} · listados {s['listados']:,} · guardados {s['guardados']:,} · "
                   f"fallidos {s['fallidos']:,}{eta}")
        out.append(f"   {last[:118]}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    a = p.parse_args()
    while True:
        db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
        text = render(db)
        db.close()
        if a.once:
            print(text)
            return
        os.system("cls" if os.name == "nt" else "clear")
        print(text, flush=True)
        time.sleep(10)


if __name__ == "__main__":
    main()
