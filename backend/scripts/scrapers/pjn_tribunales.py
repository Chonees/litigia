"""PJN Tribunales Federales y Nacionales Scraper — Sentencias de Cámaras.

Scrapes full-text sentencias (PDFs) from all federal and national courts.
Source: https://www.csjn.gov.ar/tribunales-federales-nacionales/

Strategy (proven through testing):
- 1 fresh HTTP session per search (server invalidates captcha per PHPSESSID)
- 1 search per month per cámara → POST with captcha → 20 results (page 0)
- GET sentencias.html for page 1 → 20 more results
- Total: 40 sentencias per search, most recent first
- 15s cooldown between searches to respect rate limits
- 152 months × 12 cámaras × 18 jurisdicciones = ~32K searches × 40 = ~1.3M capacity
- Checkpoint/resume: survives interruptions, skips already-scraped IDs

Usage:
    python -m scripts.scrapers.pjn_tribunales                      # 1M sentencias
    python -m scripts.scrapers.pjn_tribunales --limit 1000         # test
    python -m scripts.scrapers.pjn_tribunales --jurisdiccion 5-5   # only CABA
    python -m scripts.scrapers.pjn_tribunales --status             # progress
"""

import argparse
import asyncio
import base64
import hashlib
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from scripts.normalizers.schema import LitigiaDocument

BASE = "https://www.csjn.gov.ar/tribunales-federales-nacionales"
OUTPUT = settings.data_clean / "pjn_tribunales.jsonl"
CHECKPOINT = settings.data_logs / "pjn_tribunales_checkpoint.json"
PROGRESS = settings.data_logs / "pjn_tribunales_progress.json"

REQUEST_DELAY = 1.0
SEARCH_COOLDOWN = 15.0       # between searches — server rate limits at ~4/min
MAX_RETRIES = 5
RETRY_BACKOFF = [10, 30, 60, 120, 300]

JURISDICCIONES = {
    "5-5": "Ciudad de Buenos Aires",
    "1-1": "Buenos Aires",
    "6-6": "Cordoba",
    "13-13": "Mendoza",
    "17-17": "Salta",
    "17-10": "Jujuy",
    "7-7": "Corrientes",
    "3-3": "Chaco",
    "4-4": "Chubut",
    "8-8": "Entre Rios",
    "3-9": "Formosa",
    "1-11": "La Pampa",
    "6-12": "La Rioja",
    "14-14": "Misiones",
    "16-15": "Neuquen",
    "16-16": "Rio Negro",
    "13-18": "San Juan",
    "24-2": "Catamarca",
}


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _gen_id(source_id: str) -> str:
    return hashlib.sha256(f"pjn:{source_id}".encode()).hexdigest()[:16]


def _fmt(d: date) -> str:
    return d.strftime("%y-%m-%d")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip() or ""
    except Exception as e:
        print(f"    [{_ts()}] PDF extract failed: {e}", flush=True)
        return ""


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

class CostTracker:
    INPUT_PER_M = 1.0   # Haiku 4.5
    OUTPUT_PER_M = 5.0

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0

    def add(self, inp: int, out: int) -> None:
        self.total_input_tokens += inp
        self.total_output_tokens += out
        self.total_calls += 1

    @property
    def total_cost_usd(self) -> float:
        return (self.total_input_tokens * self.INPUT_PER_M / 1e6
                + self.total_output_tokens * self.OUTPUT_PER_M / 1e6)

    def summary(self) -> str:
        return f"${self.total_cost_usd:.4f} ({self.total_calls} captchas)"

    def to_dict(self) -> dict:
        return {"total_cost_usd": round(self.total_cost_usd, 6),
                "total_calls": self.total_calls,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens}


_cost = CostTracker()


# ---------------------------------------------------------------------------
# Captcha
# ---------------------------------------------------------------------------

def _solve_captcha(image_bytes: bytes) -> str | None:
    for attempt in range(3):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=20,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": "This is a CAPTCHA image. Read the exact characters shown. Reply with ONLY those characters, nothing else. Be precise."},
                ]}],
            )
            _cost.add(resp.usage.input_tokens, resp.usage.output_tokens)
            text = resp.content[0].text.strip().replace(" ", "")
            # Filter out garbage responses
            if len(text) >= 3 and len(text) <= 8 and not any(w in text.lower() for w in ["captcha", "image", "cannot", "can't", "sorry"]):
                print(f"    [{_ts()}] CAPTCHA solved: {text} ({_cost.summary()})", flush=True)
                return text
            print(f"    [{_ts()}] CAPTCHA bad response: '{text[:30]}', retry...", flush=True)
        except Exception as e:
            print(f"    [{_ts()}] CAPTCHA error ({attempt+1}/3): {e}", flush=True)
            time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

async def _retry(client: httpx.AsyncClient, method: str, url: str, **kw) -> httpx.Response:
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = await client.request(method, url, **kw)
            r.raise_for_status()
            return r
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError,
                httpx.RemoteProtocolError, httpx.HTTPStatusError) as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            print(f"    [{_ts()}] HTTP retry {attempt+1} in {wait}s -- {type(e).__name__}", flush=True)
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


def _new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=120.0, follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Origin": "https://www.csjn.gov.ar",
        },
    )


def _parse_results(html: str) -> list[dict]:
    results = []
    blocks = re.split(r'(?=href="[^"]*sentencia-)', html)
    for block in blocks:
        pdf_match = re.search(r'href="([^"]*sentencia-[^"]+\.pdf[^"]*)"', block)
        if not pdf_match:
            continue
        pdf_url = pdf_match.group(1)
        uuid_match = re.search(r'sentencia-(?:SGU-)?([a-f0-9-]+)\.pdf', pdf_url)
        uuid = uuid_match.group(1) if uuid_match else ""
        trib_match = re.search(r'Tribunal:\s*([^<\n]+)', block, re.IGNORECASE)
        tribunal = re.sub(r"<[^>]+>", "", trib_match.group(1) if trib_match else "").strip()
        exp_match = re.search(r'([A-Z]{2,5}\s+\d{4,}/\d{4}[^\s<]*)', block)
        expediente = exp_match.group(1) if exp_match else ""
        car_match = re.search(r'tula:\s*([^<\n]+)', block, re.IGNORECASE)
        caratula = car_match.group(1).strip() if car_match else ""
        fecha_match = re.search(r'sentencia:\s*(\d{2}/\d{2}/\d{4})', block, re.IGNORECASE)
        fecha_raw = fecha_match.group(1) if fecha_match else ""
        try:
            d, m, y = fecha_raw.split("/")
            fecha = f"{y}-{m}-{d}"
        except Exception:
            fecha = fecha_raw
        results.append({
            "pdf_url": pdf_url if pdf_url.startswith("http") else f"{BASE}/{pdf_url.lstrip('/')}",
            "uuid": uuid, "expediente": expediente, "tribunal": tribunal,
            "caratula": caratula, "fecha": fecha,
        })
    return results


# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------

def _monthly_ranges(end: date) -> list[tuple[date, date]]:
    """Newest first, down to 2013-08-21 (Ley 26.856)."""
    start_limit = date(2013, 8, 21)
    ranges = []
    cur = date(end.year, end.month, 1)
    while cur >= start_limit:
        m_start = max(cur, start_limit)
        m_end = (date(cur.year + (1 if cur.month == 12 else 0),
                      (cur.month % 12) + 1, 1) - timedelta(days=1))
        m_end = min(m_end, end)
        ranges.append((m_start, m_end))
        cur = date(cur.year, cur.month, 1) - timedelta(days=1)
        cur = date(cur.year, cur.month, 1)
    return ranges


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class PJNScraper:
    def __init__(self, limit: int = 1_000_000, jurisdiccion: str | None = None):
        self.limit = limit
        self.jur_filter = jurisdiccion
        self.scraped = 0
        self.errors = 0
        self.skipped = 0
        self.searches = 0
        self.captcha_solves = 0
        self.consecutive_fails = 0
        self.scraped_ids: set[str] = set()
        self.start_time = time.time()
        self._load_checkpoint()

    def _load_checkpoint(self) -> None:
        self.resume_key = ""
        if OUTPUT.exists() and OUTPUT.stat().st_size > 0:
            ids: set[str] = set()
            with open(OUTPUT, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sid = json.loads(line).get("source_id", "")
                        if sid:
                            ids.add(sid)
                    except json.JSONDecodeError:
                        continue
            self.scraped_ids = ids
            self.scraped = len(ids)
            if CHECKPOINT.exists():
                try:
                    cp = json.loads(CHECKPOINT.read_text())
                    self.resume_key = cp.get("resume_key", "")
                    self.searches = cp.get("searches", 0)
                except Exception:
                    pass
            if self.scraped > 0:
                print(f"  [{_ts()}] Resuming: {self.scraped:,} already scraped", flush=True)

    def _save_state(self, key: str = "") -> None:
        elapsed = time.time() - self.start_time
        rate = self.scraped / max(elapsed, 1)
        state = {
            "scraped": self.scraped, "errors": self.errors, "skipped": self.skipped,
            "searches": self.searches, "captcha_solves": self.captcha_solves,
            "api_cost": _cost.to_dict(), "resume_key": key,
            "rate_per_sec": round(rate, 2), "elapsed_seconds": round(elapsed, 1),
            "last_update": _ts(),
        }
        CHECKPOINT.write_text(json.dumps({k: v for k, v in state.items()
                                          if k != "rate_per_sec" and k != "elapsed_seconds"}))
        PROGRESS.write_text(json.dumps(state, indent=2))

    # -- Core: one search = fresh session + captcha + 2 pages (40 results) ----

    async def _do_one_search(
        self, jurisdiccion: str, camara_id: str, fecha_ini: str, fecha_fin: str,
    ) -> tuple[list[dict], httpx.AsyncClient | None]:
        """One search: fresh session → captcha → POST page 0 → GET page 1.

        Returns up to 40 results + the client (for PDF downloads).
        Never crashes.
        """
        MAX_TRIES = 5

        for attempt in range(MAX_TRIES):
            client = None
            try:
                # Cooldown — longer after failures
                wait = SEARCH_COOLDOWN + (10 * self.consecutive_fails)
                if attempt > 0:
                    wait += 10 * attempt
                    print(f"    [{_ts()}] Cooldown {wait:.0f}s (attempt {attempt+1}/{MAX_TRIES})...", flush=True)
                await asyncio.sleep(wait)

                # Fresh session
                client = _new_client()
                await _retry(client, "GET", f"{BASE}/inicio.html")
                await asyncio.sleep(REQUEST_DELAY)

                # Captcha
                cap_r = await _retry(client, "GET", f"{BASE}/lib/securimage/securimage_show.php")
                captcha = _solve_captcha(cap_r.content)
                if not captcha:
                    await client.aclose()
                    continue
                self.captcha_solves += 1
                await asyncio.sleep(REQUEST_DELAY)

                # POST — page 0
                r = await _retry(client, "POST", f"{BASE}/inicio.html", data={
                    "acc": "searchFallos", "tipo": "fallo", "paginado": "1", "pagina": "0",
                    "jurisdiccion": jurisdiccion, "camara_id": camara_id,
                    "tipofallo": "", "fecha_fallo_desde": fecha_ini, "fecha_fallo_hasta": fecha_fin,
                    "captcha_code": captcha, "tipo_oficina_id": "", "tribunal_id": "",
                    "caratula": "", "palabras_clave": "", "firmantes": "", "expediente": "", "tid": "",
                })
                await asyncio.sleep(REQUEST_DELAY)
                self.searches += 1

                html0 = r.text
                if "no ha arrojado" in html0:
                    if attempt < MAX_TRIES - 1:
                        print(f"    [{_ts()}] No results (attempt {attempt+1}/{MAX_TRIES})", flush=True)
                        await client.aclose()
                        self.consecutive_fails += 1
                        continue
                    await client.aclose()
                    return [], None

                results0 = _parse_results(html0)

                # GET — page 1
                await asyncio.sleep(REQUEST_DELAY)
                r1 = await _retry(client, "GET", f"{BASE}/sentencias.html", params={
                    "paginado": "1", "pagina": "1", "tipo": "fallo",
                })
                results1 = _parse_results(r1.text)

                # Merge & dedup
                seen = set()
                all_results = []
                for entry in results0 + results1:
                    uid = entry["uuid"] or entry["expediente"]
                    if uid and uid not in seen:
                        seen.add(uid)
                        all_results.append(entry)

                m = re.search(r"(\d[\d.]*)\s*resultado", html0)
                total_str = m.group(1) if m else "?"
                print(f"    [{_ts()}] Search OK: {total_str} total, got {len(all_results)} unique (2 pages)", flush=True)

                self.consecutive_fails = 0
                return all_results, client

            except Exception as e:
                print(f"    [{_ts()}] Search error ({attempt+1}/{MAX_TRIES}): {e}", flush=True)
                if client:
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                self.consecutive_fails += 1

        return [], None

    # -- Download PDFs --------------------------------------------------------

    async def _download_batch(
        self, client: httpx.AsyncClient, entries: list[dict], jurisdiccion: str, f_out,
    ) -> int:
        count = 0
        for entry in entries:
            if self.scraped >= self.limit:
                break
            source_id = entry["uuid"] or entry["expediente"]
            if not source_id or source_id in self.scraped_ids:
                self.skipped += 1
                continue
            try:
                pdf_r = await _retry(client, "GET", entry["pdf_url"])
                texto = _extract_pdf_text(pdf_r.content)
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"    [{_ts()}] PDF fail: {entry['expediente']} -- {type(e).__name__}: {e}", flush=True)
                self.errors += 1
                await asyncio.sleep(2)
                continue
            if not texto or len(texto) < 300:
                self.skipped += 1
                continue

            doc = LitigiaDocument(
                id=_gen_id(source_id), source="pjn_tribunales", source_id=source_id,
                texto=texto, sumario="",
                caratula=entry["caratula"] or entry["expediente"],
                tipo_documento="fallo", tipo_fallo="sentencia",
                tribunal=entry["tribunal"], tipo_tribunal="camara",
                fecha=entry["fecha"],
                jurisdiccion=JURISDICCIONES.get(jurisdiccion, jurisdiccion),
            )
            f_out.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")
            f_out.flush()
            self.scraped_ids.add(source_id)
            self.scraped += 1
            count += 1

            if self.scraped % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = self.scraped / max(elapsed, 1)
                print(
                    f"    [{_ts()}] {self.scraped:,} | {entry['tribunal'][:40]} | "
                    f"{entry['fecha']} | {len(texto):,} chars | {rate:.1f}/s",
                    flush=True,
                )
        return count

    # -- Main loop ------------------------------------------------------------

    async def run(self) -> None:
        settings.ensure_dirs()
        months = _monthly_ranges(date.today())

        jurisdicciones = {self.jur_filter: JURISDICCIONES.get(self.jur_filter, "")} \
            if self.jur_filter else JURISDICCIONES

        print(f"\n{'='*60}")
        print(f"  [{_ts()}] PJN Tribunales Scraper")
        print(f"  Target: {self.limit:,} sentencias (most recent first)")
        print(f"  Output: {OUTPUT}")
        print(f"  {len(months)} months x {len(jurisdicciones)} jurisdicciones")
        print(f"  40 sentencias/search, {SEARCH_COOLDOWN}s cooldown")
        print(f"{'='*60}")

        found_resume = not bool(self.resume_key)
        meta_client = _new_client()
        await _retry(meta_client, "GET", f"{BASE}/inicio.html")

        try:
            mode = "a" if self.scraped > 0 else "w"
            with open(OUTPUT, mode, encoding="utf-8") as f:
                for jur_code, jur_name in jurisdicciones.items():
                    if self.scraped >= self.limit:
                        break

                    camaras = []
                    try:
                        r = await _retry(meta_client, "GET",
                                         f"{BASE}/ajax/request_tribunales_fallos_new.php",
                                         params={"jurisdiccion": jur_code})
                        camaras = re.findall(r'value="([^"]+)"[^>]*>([^<]+)', r.text)
                    except Exception as e:
                        print(f"  [{_ts()}] Camaras error {jur_name}: {e}", flush=True)

                    if not camaras:
                        print(f"  [{_ts()}] No camaras for {jur_name}", flush=True)
                        continue
                    print(f"\n  [{_ts()}] {jur_name}: {len(camaras)} camaras", flush=True)

                    for cam_id, cam_name in camaras:
                        if self.scraped >= self.limit:
                            break

                        for m_start, m_end in months:
                            if self.scraped >= self.limit:
                                break

                            key = f"{jur_code}:{cam_id}:{m_start}"
                            if not found_resume:
                                if key == self.resume_key:
                                    found_resume = True
                                else:
                                    continue

                            try:
                                results, client = await self._do_one_search(
                                    jur_code, cam_id, _fmt(m_start), _fmt(m_end),
                                )
                                count = 0
                                if results and client:
                                    count = await self._download_batch(
                                        client, results, jur_code, f,
                                    )
                                    await client.aclose()
                            except Exception as e:
                                print(f"  [{_ts()}] SKIP {cam_name} {m_start} -- {type(e).__name__}: {e}", flush=True)
                                self.errors += 1
                                count = 0
                                await asyncio.sleep(10)

                            elapsed = time.time() - self.start_time
                            rate = self.scraped / max(elapsed, 1)
                            eta_hours = (self.limit - self.scraped) / max(rate, 0.001) / 3600
                            print(
                                f"  [{_ts()}] {cam_name[:30]} {m_start} | "
                                f"+{count} | total: {self.scraped:,} | "
                                f"err: {self.errors} | {_cost.summary()} | "
                                f"{rate:.1f}/s | ETA: {eta_hours:.1f}h",
                                flush=True,
                            )
                            self._save_state(key)

        finally:
            await meta_client.aclose()

        self._save_state()
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"  [{_ts()}] DONE")
        print(f"  Sentencias: {self.scraped:,}")
        print(f"  Searches: {self.searches:,}")
        print(f"  Errors: {self.errors}")
        print(f"  Time: {elapsed/3600:.1f} hours")
        print(f"  API cost: {_cost.summary()}")
        print(f"{'='*60}")


def show_status():
    if PROGRESS.exists():
        data = json.loads(PROGRESS.read_text())
        for k, v in data.items():
            if k == "api_cost" and isinstance(v, dict):
                print(f"  api_cost: ${v.get('total_cost_usd', 0):.4f} ({v.get('total_calls', 0)} captchas)")
            else:
                print(f"  {k}: {v}")
    if OUTPUT.exists():
        size = OUTPUT.stat().st_size / (1024 * 1024)
        lines = sum(1 for _ in open(OUTPUT, encoding="utf-8"))
        print(f"  file_size: {size:.1f} MB")
        print(f"  documents: {lines:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1_000_000)
    parser.add_argument("--jurisdiccion", type=str, help="e.g. 5-5 for CABA")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        asyncio.run(PJNScraper(limit=args.limit, jurisdiccion=args.jurisdiccion).run())
