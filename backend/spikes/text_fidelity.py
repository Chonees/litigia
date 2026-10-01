"""Text fidelity: re-download a random sample of PDFs and compare with the stored, cleaned text.

Usage (from backend/): python -m spikes.text_fidelity --n 50 [--camara C_7]
"""

import argparse
import difflib
import random
import sqlite3
import time

import httpx

from scripts import quality
from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO, REQUEST_DELAY, extract_pdf_text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--camara", choices=list(CAMARA_FUERO), help="default: every fuero")
    a = p.parse_args()
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    where, params = ("AND fuero=?", (CAMARA_FUERO[a.camara],)) if a.camara else ("", ())
    rows = db.execute("SELECT id, url, texto, caratula FROM documents WHERE source='pjn' AND active=1 "
                      f"AND fecha >= '2025-09-27' AND url<>'' {where} ORDER BY id", params).fetchall()
    sample = random.Random(20260928).sample(rows, a.n)
    identical = similar = different = failed = 0
    ratios = []
    with httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as c:
        for doc_id, url, stored, car in sample:
            try:
                raw = extract_pdf_text(c.get(url).content)
            except Exception as e:
                failed += 1
                print(f"  descarga falló {doc_id}: {type(e).__name__}")
                continue
            fresh = quality.strip_noise_paragraphs(quality.clean_pjn_text(raw))
            if fresh == stored:
                identical += 1
                ratios.append(1.0)
            else:
                r = difflib.SequenceMatcher(None, fresh, stored, autojunk=False).ratio()
                ratios.append(r)
                similar += r >= 0.99
                different += r < 0.99
                print(f"  distinto {doc_id} ratio {r:.4f} | {car[:50]} | nuevo {len(fresh)} vs guardado {len(stored)}")
            # every word of the raw PDF body should survive cleaning (only stamps/signatures/headers go)
            time.sleep(REQUEST_DELAY)          # the site tolerates ~1 request/s per IP
    n = a.n - failed
    print(f"\n{a.n} PDFs · idénticos {identical} · casi idénticos (≥99%) {similar} · distintos {different} · fallaron {failed}")
    print(f"similitud media {sum(ratios) / max(1, len(ratios)):.4f} · mínima {min(ratios) if ratios else 0:.4f}")


if __name__ == "__main__":
    main()
