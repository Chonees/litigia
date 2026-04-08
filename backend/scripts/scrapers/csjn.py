"""CSJN Fallos Scraper — Corte Suprema de Justicia de la Nacion.

Strategy:
1. GET consultaAcuerdo.html?fecha=DD/MM/YYYY → sets server session
2. GET paginarFallos.html?jtStartIndex=0 → JSON with Records (codigo, idAnalisis, caratula, etc.)
3. Paginate through all results
4. For each fallo: GET getDocumentos.html?idAnalisis=ID → document links
5. GET verDocumentoByIdLinksJSP.html?idDocumento=ID → full text
6. Save as LitigiaDocument JSONL

Usage:
    python -m scripts.scrapers.csjn                    # scrape 100K fallos
    python -m scripts.scrapers.csjn --limit 1000       # test with 1000
    python -m scripts.scrapers.csjn --year 2024        # only year
    python -m scripts.scrapers.csjn --status            # show progress
"""

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from scripts.normalizers.schema import LitigiaDocument

BASE = "https://sjconsulta.csjn.gov.ar/sjconsulta"
OUTPUT = settings.data_clean / "csjn.jsonl"
CHECKPOINT = settings.data_logs / "csjn_checkpoint.json"
PROGRESS = settings.data_logs / "csjn_progress.json"

REQUEST_DELAY = 0.3


def _gen_id(doc_id: str) -> str:
    return hashlib.sha256(f"csjn:{doc_id}".encode()).hexdigest()[:16]


def _clean_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class CSJNScraper:
    def __init__(self, limit: int = 100_000, year: int | None = None):
        self.limit = limit
        self.year_filter = year
        self.scraped = 0
        self.errors = 0
        self.skipped = 0
        self.scraped_ids: set[str] = set()
        self.start_time = time.time()
        self._load_checkpoint()

    def _load_checkpoint(self) -> None:
        if CHECKPOINT.exists():
            data = json.loads(CHECKPOINT.read_text())
            self.scraped_ids = set(data.get("scraped_ids", []))
            self.scraped = data.get("scraped", 0)
            self.errors = data.get("errors", 0)
            if self.scraped > 0:
                print(f"  Resuming: {self.scraped:,} already scraped")

    def _save_checkpoint(self) -> None:
        CHECKPOINT.write_text(json.dumps({
            "scraped": self.scraped,
            "errors": self.errors,
            "scraped_ids": list(self.scraped_ids)[-50000:],
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
        }))

    def _save_progress(self, total_dates: int, dates_done: int) -> None:
        elapsed = time.time() - self.start_time
        rate = self.scraped / max(elapsed, 1)
        PROGRESS.write_text(json.dumps({
            "scraped": self.scraped,
            "errors": self.errors,
            "skipped": self.skipped,
            "dates_total": total_dates,
            "dates_done": dates_done,
            "percent": round(dates_done / max(total_dates, 1) * 100, 1),
            "rate_per_sec": round(rate, 2),
            "elapsed_seconds": round(elapsed, 1),
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, indent=2))

    async def get_dates(self, client: httpx.AsyncClient) -> list[str]:
        """Get all acuerdo dates."""
        r = await client.get(f"{BASE}/acuerdos/verFechasAcuerdos.html")
        r.raise_for_status()
        dates = r.json()
        if self.year_filter:
            dates = [d for d in dates if d.endswith(str(self.year_filter))]
        dates.sort(key=lambda d: d.split("/")[::-1], reverse=True)  # newest first
        return dates

    async def get_fallos_page(
        self, client: httpx.AsyncClient, start_index: int
    ) -> tuple[list[dict], int]:
        """Get one page of fallos from the paginator. Returns (records, total)."""
        r = await client.get(
            f"{BASE}/fallos/paginarFallos.html",
            params={"jtStartIndex": start_index},
        )
        r.raise_for_status()
        data = r.json()

        if data.get("Result") != "OK":
            return [], 0

        records = data.get("Records", [])
        total = data.get("TotalRecordCount", 0)
        return records, total

    async def get_document_text(self, client: httpx.AsyncClient, codigo: str) -> str:
        """Get full text by downloading the PDF and extracting text."""
        try:
            r = await client.get(
                f"{BASE}/documentos/verDocumentoById.html",
                params={"idDocumento": codigo},
            )
            r.raise_for_status()

            if b"%PDF" not in r.content[:10]:
                # Not a PDF, try HTML fallback
                return _clean_html(r.text) if len(r.text) > 500 else ""

            # Extract text from PDF in memory
            import pymupdf

            doc = pymupdf.open(stream=r.content, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()

            text = "\n".join(text_parts).strip()
            return text if len(text) > 200 else ""
        except Exception:
            return ""

    async def scrape_date(self, client: httpx.AsyncClient, fecha: str, f_out) -> int:
        """Scrape all fallos for one date. Returns count scraped."""
        count = 0

        # Init session with the date
        await client.get(f"{BASE}/fallos/consultaAcuerdo.html", params={"fecha": fecha})
        await asyncio.sleep(REQUEST_DELAY)

        # Paginate through results
        start = 0
        while True:
            records, total = await self.get_fallos_page(client, start)
            if not records:
                break

            for rec in records:
                if self.scraped >= self.limit:
                    return count

                codigo = str(rec.get("codigo", ""))
                id_analisis = str(rec.get("idAnalisis", ""))

                if codigo in self.scraped_ids:
                    self.skipped += 1
                    continue

                # Get full text using codigo as document ID
                texto = await self.get_document_text(client, codigo)
                await asyncio.sleep(REQUEST_DELAY)

                if not texto or len(texto) < 300:
                    self.skipped += 1
                    continue

                # Extract metadata from record
                voces_raw = rec.get("voces", "") or ""
                voces = [v.strip() for v in voces_raw.split(",") if v.strip()] if voces_raw else []

                magistrados_raw = rec.get("magistrados", "") or rec.get("jueces", "") or ""
                magistrados = [m.strip() for m in magistrados_raw.split(",") if m.strip()] if magistrados_raw else []

                doc = LitigiaDocument(
                    id=_gen_id(codigo or id_analisis),
                    source="csjn",
                    source_id=codigo or id_analisis,
                    texto=texto,
                    sumario=str(rec.get("sumario", "") or rec.get("sintesis", "") or ""),
                    caratula=str(rec.get("caratula", "") or rec.get("titulo", "") or ""),
                    tipo_documento="fallo",
                    tipo_fallo=str(rec.get("tipoFallo", "") or "sentencia"),
                    tribunal="Corte Suprema de Justicia de la Nacion",
                    tipo_tribunal="corte_suprema",
                    magistrados=magistrados,
                    materia=str(rec.get("materia", "") or ""),
                    voces=voces,
                    fecha=str(rec.get("fecha", "") or fecha),
                    jurisdiccion="Nacional",
                    provincia="Ciudad Autonoma de Buenos Aires",
                )

                f_out.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")
                f_out.flush()

                self.scraped_ids.add(codigo)
                if id_analisis:
                    self.scraped_ids.add(id_analisis)
                self.scraped += 1
                count += 1

            start += len(records)
            if start >= total:
                break
            await asyncio.sleep(REQUEST_DELAY)

        return count

    async def run(self) -> None:
        settings.ensure_dirs()

        print(f"\n{'='*55}")
        print(f"  CSJN Scraper — Corte Suprema")
        print(f"  Target: {self.limit:,} fallos completos")
        print(f"  Output: {OUTPUT}")
        print(f"{'='*55}")

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "LITIGIA-Research/0.1 (legal-academic-research)",
                "Accept": "text/html,application/json,*/*",
            },
        ) as client:
            dates = await self.get_dates(client)
            print(f"  {len(dates)} dates found")
            total_dates = len(dates)

            mode = "a" if self.scraped > 0 else "w"
            with open(OUTPUT, mode, encoding="utf-8") as f:
                for i, fecha in enumerate(dates):
                    if self.scraped >= self.limit:
                        break

                    count = await self.scrape_date(client, fecha, f)

                    if (i + 1) % 3 == 0 or count > 0:
                        elapsed = time.time() - self.start_time
                        rate = self.scraped / max(elapsed, 1)
                        eta = (self.limit - self.scraped) / max(rate, 0.01) / 60
                        print(
                            f"  [{i+1}/{total_dates}] {fecha} | "
                            f"{self.scraped:,} scraped | {self.skipped:,} skipped | "
                            f"{rate:.1f}/s | ETA: {eta:.0f}min"
                        )
                        self._save_checkpoint()
                        self._save_progress(total_dates, i + 1)

        self._save_checkpoint()
        print(f"\n  Done: {self.scraped:,} fallos | {self.errors} errors")


def show_status():
    if PROGRESS.exists():
        data = json.loads(PROGRESS.read_text())
        for k, v in data.items():
            print(f"  {k}: {v}")
    if OUTPUT.exists():
        size = OUTPUT.stat().st_size / (1024 * 1024)
        lines = sum(1 for _ in open(OUTPUT, encoding="utf-8"))
        print(f"  file_size: {size:.1f} MB")
        print(f"  documents: {lines:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100_000)
    parser.add_argument("--year", type=int)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        if CHECKPOINT.exists():
            CHECKPOINT.unlink()
        CSJNScraper(limit=args.limit, year=args.year)
        asyncio.run(CSJNScraper(limit=args.limit, year=args.year).run())
