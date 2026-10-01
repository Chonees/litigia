"""Every INTERVAL: status of the VPS, collect + merge into the local catalog, accounting per cámara.

Collecting often means a VPS that is cut off (billing, crash) loses at most one interval of work.
Prints one "WATCH" line per round plus one line per cámara; exits after a final collect once every
VPS has stopped. Usage (from backend/): python -u -m spikes.watch_parallel
"""

import sqlite3
import time
from datetime import date

from scripts.config import settings
from scripts.reconcile import Leaf, accounts
from scripts.scrapers import deploy_parallel as dp
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO

INTERVAL = 900
DESDE, HASTA = date(2025, 9, 27), date(2026, 9, 27)


def accounting(camaras: list[str]) -> list[str]:
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    lines = []
    for c in camaras:
        leaves, uncovered = accounts(db, c, DESDE, HASTA)
        t = Leaf("", "")
        for leaf in leaves:
            t.add(leaf)
        pct = f"{t.guardados / t.sitio:.1%}" if t.sitio else "-"
        lines.append(f"   {c:<5} {CAMARA_FUERO[c]:<34} sitio {t.sitio:>6,} · guardados {t.guardados:>6,} ({pct}) · "
                     f"fallidos {t.fallidos:,} · no listados {t.no_listados:,} · días sin cubrir {len(uncovered)}")
    db.close()
    return lines


def main() -> None:
    camaras = sorted({i.get("camara", "") for i in dp._load_state()["instances"] if not i.get("destroyed")} - {""})
    stopped_rounds = 0
    while True:
        rows = dp.status()
        # A VPS that did not answer (SSH timeout under load) counts as alive: only an explicit "stopped" from
        # every VPS, two rounds in a row, ends the watch. Stopping early would stop collecting.
        alive = sum(1 for r in rows if r.get("alive") or "error" in r or "alive" not in r)
        docs = sum(sum(r.get("status", {}).values()) for r in rows)
        merged = dp.collect()
        print(f"WATCH {time.strftime('%H:%M')} · vivas {alive}/{len(rows)} · docs en VPS {docs:,} · "
              f"traídos nuevos {merged['new']:,} · fallidos {merged['failures']:,}", flush=True)
        for line in accounting(camaras):
            print(line, flush=True)
        stopped_rounds = stopped_rounds + 1 if alive == 0 else 0
        if stopped_rounds >= 2:
            print("WATCH DONE: todas las VPS terminaron y se trajo todo", flush=True)
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
