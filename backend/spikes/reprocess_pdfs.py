"""Re-download every active PJN ruling's PDF and re-clean it with the current rules.

Recovers content the old cleaning dropped (numeric tables) and refreshes firmantes. Only the
text is replaced; metadata stays. Resumable: finished ids go to logs/reprocess_done.txt.

Rate-limited on purpose: 6 unthrottled workers (~40 PDFs/s) got our IP blocked by csjn.gov.ar
on 2026-09-28. The scrapers ran for hours at ~1 request/s per IP without trouble.
Usage (from backend/): python -u -m spikes.reprocess_pdfs [--workers 2] [--rate 2]
"""

import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from scripts import quality
from scripts.catalog import Catalog
from scripts.config import settings
from scripts.scrapers.pjn_tribunales import extract_pdf_text

DONE = settings.data_logs / "reprocess_done.txt"


class RateLimit:
    """At most `per_second` requests across all threads."""

    def __init__(self, per_second: float):
        self.interval = 1 / per_second
        self.next = time.monotonic()
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            self.next = max(self.next, now)
            delay = self.next - now
            self.next += self.interval
        time.sleep(delay)


def fetch(client: httpx.Client, limit: RateLimit, url: str) -> tuple[str, list[str]] | None:
    """(clean text, firmantes), or None after 3 failed attempts (e.g. the site serves an empty PDF)."""
    for attempt in range(3):
        limit.wait()
        try:
            raw = extract_pdf_text(client.get(url).content)
            firmantes, _ = quality.extract_firmantes(raw)
            return quality.clean_pjn_text(raw), firmantes
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--rate", type=float, default=2.0, help="max PDFs per second, all workers together")
    a = p.parse_args()
    cat = Catalog(settings.data_root / "catalog.db")
    done = set(DONE.read_text().split()) if DONE.exists() else set()
    rows = [r for r in cat.db.execute(
        "SELECT source_id, url, text_hash FROM documents WHERE source='pjn' AND active=1 AND url<>'' ORDER BY fecha DESC")
        if r["source_id"] not in done]
    print(f"{len(rows)} PDFs por reprocesar ({len(done)} ya hechos)", flush=True)
    changed = failed = 0
    t0 = time.time()
    limit = RateLimit(a.rate)
    client = httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    with ThreadPoolExecutor(a.workers) as pool, DONE.open("a") as log:
        for k, (row, res) in enumerate(zip(rows, pool.map(lambda r: fetch(client, limit, r["url"]), rows)), 1):
            if res is None:
                failed += 1
            else:
                texto, firmantes = res
                if texto and quality.text_hash(quality.strip_noise_paragraphs(texto)) != row["text_hash"]:
                    cat.upsert({"source": "pjn", "source_id": row["source_id"], "texto": texto,
                                "firmantes": firmantes}, commit=False)
                    changed += 1
                log.write(row["source_id"] + "\n")
            if k % 500 == 0:
                cat.db.commit()
                log.flush()
                rate = k / (time.time() - t0)
                print(f"[{time.strftime('%H:%M:%S')}] {k}/{len(rows)} · cambiaron {changed} · fallaron {failed} · "
                      f"{rate:.1f}/s · faltan ~{(len(rows) - k) / rate / 60:.0f} min", flush=True)
    cat.db.commit()
    client.close()
    cat.close()
    print(f"DONE {len(rows)} reprocesados · texto cambió en {changed} · fallaron {failed}", flush=True)


if __name__ == "__main__":
    main()
