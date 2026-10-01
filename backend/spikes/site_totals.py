"""How many rulings the site reports per cámara and tipo for a date range: one first-page search each.

Cheap sizing before a scrape (no PDFs, no extra pages). Spaced out so it can run next to a scraper.
Usage (from backend/): python -m spikes.site_totals --desde 2025-09-27 --hasta 2026-09-27 C_1:D C_10:D C_1:I
"""

import argparse
import time
from datetime import date

from scripts.scrapers.pjn_tribunales import CaptchaSolver, site_total

SPACING = 45.0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--desde", type=date.fromisoformat, required=True)
    p.add_argument("--hasta", type=date.fromisoformat, required=True)
    p.add_argument("pairs", nargs="+", help="camara:tipo, e.g. C_1:D")
    a = p.parse_args()
    solver = CaptchaSolver()
    for i, pair in enumerate(a.pairs):
        if i:
            time.sleep(SPACING)
        camara, tipo = pair.split(":")
        print(f"{camara} {tipo} {a.desde}..{a.hasta}: {site_total(solver, camara, tipo, a.desde, a.hasta)}", flush=True)
    print(f"captcha ${solver.cost:.4f}", flush=True)


if __name__ == "__main__":
    main()
