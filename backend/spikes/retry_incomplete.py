"""Find CNAT days where the catalog holds fewer rulings than the site reported, and re-scrape them.

For each incomplete day: forget its finished searches (cámara, group and oficina level) and run
the scraper for that single day. Known rulings are only refreshed; missing ones are downloaded
again. PDFs the site keeps serving empty stay missing and are listed at the end.

Usage (from backend/): python -m spikes.retry_incomplete --desde 2025-09-27 --hasta 2026-09-27 [--dry-run]
"""

import argparse
import sqlite3
from datetime import date

from scripts.catalog import Catalog
from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CaptchaSolver, PJNScraper, PJNSite

JUR, CAMARA, TIPO = "5-5", "C_7", "D"


def incomplete_days(db: sqlite3.Connection, desde: str, hasta: str) -> list[tuple[str, str, int, int]]:
    out = []
    for key, total in db.execute(
            "SELECT key, total FROM searches WHERE source='pjn' AND split=0 AND key LIKE ? "
            "AND substr(key, -21, 10) >= ? AND substr(key, -10) <= ?", (f"{JUR}|{CAMARA}|*|%", desde, hasta)):
        s, e = key.split("|")[-2:]
        have = db.execute("SELECT COUNT(*) FROM documents WHERE source='pjn' AND tribunal LIKE '%TRABAJO%' "
                          "AND fecha BETWEEN ? AND ?", (s, e)).fetchone()[0]
        if have < total:
            out.append((s, e, total, have))
    return sorted(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True)
    p.add_argument("--hasta", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    cat = Catalog(settings.data_root / "catalog.db")
    days = incomplete_days(cat.db, a.desde, a.hasta)
    print(f"{len(days)} tramos incompletos · faltan {sum(t - h for _, _, t, h in days)} fallos")
    for s, e, t, h in days:
        print(f"  {s}..{e}: sitio {t} · catálogo {h} · faltan {t - h}")
    if a.dry_run or not days:
        cat.close()
        return
    scraper = PJNScraper(cat, PJNSite(CaptchaSolver()), limit=10_000_000)
    for s, e, _, _ in days:
        cat.db.execute("DELETE FROM searches WHERE source='pjn' AND key LIKE ?", (f"{JUR}|{CAMARA}|%|{TIPO}|{s}|{e}",))
        cat.db.commit()
        scraper.run(JUR, CAMARA, TIPO, date.fromisoformat(s), date.fromisoformat(e))
    after = incomplete_days(cat.db, a.desde, a.hasta)
    print(f"\nDespués del reintento: {len(after)} tramos incompletos · faltan {sum(t - h for _, _, t, h in after)} fallos")
    for s, e, t, h in after:
        print(f"  {s}..{e}: sitio {t} · catálogo {h} · faltan {t - h}")
    print(f"captcha ${scraper.site.solver.cost:.4f} · nuevos {scraper.new} · errores {scraper.errors}")
    cat.close()


if __name__ == "__main__":
    main()
