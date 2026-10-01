"""Find days where the catalog holds fewer rulings than the site reported, and re-scrape them.

Incomplete means, per finished search (scripts/reconcile.py): rulings the site counted but never listed,
listed rulings not stored (failed PDFs are tried again), or, for searches older than the listings table,
fewer rulings by date than the site's total. Days no finished search covers are retried too.

For each incomplete day: forget its finished searches (cámara, group and oficina level) and run
the scraper for that single day. Known rulings are only refreshed; missing ones are downloaded
again. PDFs the site keeps serving empty stay missing and are listed at the end.

Usage (from backend/): python -m spikes.retry_incomplete --desde 2025-09-27 --hasta 2026-09-27 [--camara C_7] [--dry-run]
"""

import argparse
import sqlite3
from datetime import date

from scripts.catalog import Catalog
from scripts.config import settings
from scripts.reconcile import accounts
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO, CaptchaSolver, PJNScraper, PJNSite

JUR, TIPO = "5-5", "D"


def incomplete_days(db: sqlite3.Connection, desde: str, hasta: str, camara: str = "C_7") -> list[tuple[str, str, int, int]]:
    """(start, end, site total, stored) per incomplete search; uncovered days come with total -1."""
    leaves, uncovered = accounts(db, camara, date.fromisoformat(desde), date.fromisoformat(hasta), jur=JUR, tipo=TIPO)
    out = []
    for leaf in leaves:
        have = leaf.guardados if leaf.listados else min(leaf.por_fecha, leaf.sitio)
        if have < leaf.sitio:
            out.append((leaf.start, leaf.end, leaf.sitio, have))
    out += [(d.isoformat(), d.isoformat(), -1, 0) for d in uncovered]
    return sorted(out)


def _report(title: str, days: list[tuple[str, str, int, int]]) -> None:
    missing = sum(t - h for _, _, t, h in days if t >= 0)
    print(f"{title}{len(days)} tramos incompletos · faltan {missing} fallos (+ {sum(1 for d in days if d[2] < 0)} días sin cubrir)")
    for s, e, t, h in days:
        print(f"  {s}..{e}: " + (f"sitio {t} · catálogo {h} · faltan {t - h}" if t >= 0 else "sin cubrir"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True)
    p.add_argument("--hasta", required=True)
    p.add_argument("--camara", default="C_7", choices=list(CAMARA_FUERO))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    cat = Catalog(settings.data_root / "catalog.db")
    days = incomplete_days(cat.db, a.desde, a.hasta, a.camara)
    _report("", days)
    if a.dry_run or not days:
        cat.close()
        return
    scraper = PJNScraper(cat, PJNSite(CaptchaSolver()), limit=10_000_000)
    for s, e, _, _ in days:
        cat.db.execute("DELETE FROM searches WHERE source='pjn' AND key LIKE ?", (f"{JUR}|{a.camara}|%|{TIPO}|{s}|{e}",))
        cat.db.commit()
        scraper.run(JUR, a.camara, TIPO, date.fromisoformat(s), date.fromisoformat(e))
    after = incomplete_days(cat.db, a.desde, a.hasta, a.camara)
    _report("\nDespués del reintento: ", after)
    print(f"captcha ${scraper.site.solver.cost:.4f} · nuevos {scraper.new} · errores {scraper.errors}")
    cat.close()


if __name__ == "__main__":
    main()
