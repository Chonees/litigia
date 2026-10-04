"""PJN Tribunales Federales y Nacionales — full-text sentencias into the catalog.

Source: https://www.csjn.gov.ar/tribunales-federales-nacionales/ (backend: cij.gov.ar)

How it works:
- Searches need a fresh session + captcha (solved with Haiku, ~$0.0001 each).
  The filter is the hidden `tid` field (cámara, or a Sala/juzgado). Each search
  returns at most 100 results (5 pages, re-posting the form with its token) but
  reports the real total. `pjn_parse.crawl` splits the date range until each
  search fits; a single day over 100 is split by Sala. Nothing is silently dropped.
- Metadata (tribunal with Sala, expediente, carátula, fecha) comes from the
  results page; firmantes and signature date from the PDF itself.
- PDFs download without a session. Text is cleaned and split into paragraphs,
  then `catalog.upsert` applies the data contract (scripts/quality.py).
- Results already in the catalog are not downloaded again, only their metadata
  is refreshed. Every search is recorded, so runs resume where they stopped and
  `python -m scripts.audit` can measure completeness against the site.

Usage (from backend/):
    python -m scripts.scrapers.pjn_tribunales --jurisdiccion 5-5 --camara C_7 --desde 2024-03-01 --hasta 2024-03-31
    python -m scripts.scrapers.pjn_tribunales --jurisdiccion 5-5          # every cámara, definitivas, 2013 → today
    python -m scripts.scrapers.pjn_tribunales --tipo I                    # interlocutorias instead
    python -m scripts.scrapers.pjn_tribunales --list-camaras 5-5
"""

import argparse
import base64
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts import quality
from scripts.catalog import Catalog
from scripts.config import settings
from scripts.scrapers.pjn_parse import CAP, PAGE_SIZE, crawl, parse_oficinas, parse_results, parse_token, parse_total

SOURCE = "pjn"
BASE = "https://www.csjn.gov.ar/tribunales-federales-nacionales"
FIRST_DATE = date(2013, 8, 21)   # Ley 26.856: publication of sentencias starts

REQUEST_DELAY = 1.0
SEARCH_COOLDOWN = 15.0           # the server rate-limits at ~4 searches/min per IP
SEARCH_ATTEMPTS = 5
HTTP_RETRIES = 4
HTTP_BACKOFF = [10, 30, 60, 120]

# Tipos de oficina in the site's form: Sala, Juzgado, Secretaría Especial, Tribunal Oral, Oficina Judicial
OFICINA_TIPOS = ("3", "1", "8", "9", "167")
EXPEDIENTE_FIRST_YEAR = 1990     # oldest case year tried when one oficina's day is split by case year

TIPOS = {"D": "Definitiva", "I": "Interlocutoria", "P": "Plenario", "V": "Veredicto"}

# Cámaras collected so far (CABA) and the `fuero` that quality.detect_fuero gives their rulings,
# so audits can select one cámara's documents (Sala and juzgado alike) by that column.
CAMARA_FUERO = {
    "C_7": "laboral",
    "C_1": "civil",
    "C_10": "comercial",
    "C_5": "seguridad social",
    "C_2": "contencioso administrativo federal",
}

JURISDICCIONES = {
    "5-5": "Ciudad de Buenos Aires",
    "1-1": "Buenos Aires",
    "24-2": "Catamarca",
    "3-3": "Chaco",
    "4-4": "Chubut",
    "6-6": "Córdoba",
    "7-7": "Corrientes",
    "8-8": "Entre Ríos",
    "3-9": "Formosa",
    "17-10": "Jujuy",
    "1-11": "La Pampa",
    "6-12": "La Rioja",
    "13-13": "Mendoza",
    "14-14": "Misiones",
    "16-15": "Neuquén",
    "16-16": "Río Negro",
    "17-17": "Salta",
    "13-18": "San Juan",
    "13-19": "San Luis",
    "4-20": "Santa Cruz",
    "21-21": "Santa Fe",
    "24-22": "Santiago del Estero",
    "4-23": "Tierra del Fuego",
}


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# -- HTTP ---------------------------------------------------------------------------

def _client() -> httpx.Client:
    return httpx.Client(
        timeout=120.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Origin": "https://www.csjn.gov.ar",
        },
    )


def _get(client: httpx.Client, method: str, url: str, **kw) -> httpx.Response:
    for attempt in range(HTTP_RETRIES + 1):
        try:
            r = client.request(method, url, **kw)
            r.raise_for_status()
            return r
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            if attempt == HTTP_RETRIES:
                raise
            wait = HTTP_BACKOFF[min(attempt, len(HTTP_BACKOFF) - 1)]
            log(f"  HTTP retry {attempt + 1} in {wait}s ({type(e).__name__})")
            time.sleep(wait)
    raise RuntimeError("unreachable")


# -- Captcha ------------------------------------------------------------------------

FATAL_API_ERRORS = ("AuthenticationError", "PermissionDeniedError", "BadRequestError")


def client_kwargs(api_key: str, workspace_id: str) -> dict:
    """Keys not scoped to a workspace need the workspace id on every request."""
    kwargs: dict = {"api_key": api_key}
    if workspace_id:
        kwargs["default_headers"] = {"anthropic-workspace-id": workspace_id}
    return kwargs


class CaptchaSolver:
    INPUT_PER_M, OUTPUT_PER_M = 1.0, 5.0   # Haiku 4.5, USD per million tokens

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(**client_kwargs(settings.anthropic_api_key, settings.anthropic_workspace_id))
        self.calls = 0
        self.cost = 0.0

    def solve(self, image: bytes) -> str | None:
        """Read the captcha. Configuration errors (auth, permission, bad request) propagate:
        retrying cannot fix them."""
        import anthropic
        fatal = tuple(getattr(anthropic, name) for name in FATAL_API_ERRORS)
        for _ in range(3):
            try:
                resp = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=20,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                     "data": base64.standard_b64encode(image).decode()}},
                        {"type": "text", "text": "This is a CAPTCHA image. Read the exact characters shown. "
                                                 "Reply with ONLY those characters, nothing else. Be precise."},
                    ]}],
                )
                self.calls += 1
                self.cost += (resp.usage.input_tokens * self.INPUT_PER_M
                              + resp.usage.output_tokens * self.OUTPUT_PER_M) / 1e6
                text = resp.content[0].text.strip().replace(" ", "")
                if 3 <= len(text) <= 8 and text.isalnum():
                    return text
            except fatal:
                raise
            except Exception as e:
                log(f"  captcha error: {e}")
                time.sleep(2)
        return None


# -- Site ---------------------------------------------------------------------------

class PJNSite:
    def __init__(self, solver: CaptchaSolver):
        self.solver = solver
        self.searches = 0
        self.fails = 0

    def camaras(self, jurisdiccion: str) -> list[tuple[str, str]]:
        with _client() as c:
            r = _get(c, "GET", f"{BASE}/ajax/request_tribunales_fallos_new.php", params={"jurisdiccion": jurisdiccion})
        return [(cid, name.strip()) for cid, name in re.findall(r'value="([^"]+)"[^>]*>([^<]+)', r.text) if cid]

    def oficinas(self, camara: str, tipo_oficina: str = "") -> list[tuple[str, str]]:
        """Offices (Salas, juzgados…) under a cámara, optionally of one tipo de oficina."""
        params = {"tid": camara, **({"tipo_oficina_id": tipo_oficina} if tipo_oficina else {})}
        with _client() as c:
            r = _get(c, "GET", f"{BASE}/ajax/request_tribunales_fallos_new.php", params=params)
        return parse_oficinas(r.text)

    def search(self, jurisdiccion: str, camara: str, oficina: str, tipo: str,
               start: date, end: date, tipo_oficina: str = "", expediente: str = "",
               caratula: str = "") -> tuple[int, list[dict]]:
        """One search, every page the site allows. Returns (site total, up to CAP results).

        The site filters by `tid` (a cámara such as C_7, or an office such as T_7_TS1);
        `camara_id` alone is ignored. Next pages re-post the form with the returned token.
        `expediente` matches part of the case number: "/2021" returns only the 2021 cases (verified live).
        """
        form = {
            "acc": "searchFallos", "tipo": "fallo", "paginado": "1", "pagina": "0", "token": "",
            "jurisdiccion": jurisdiccion, "camara_id": camara, "tribunal_id": oficina,
            "tid": oficina or camara, "tipo_oficina_id": tipo_oficina, "tipofallo": tipo,
            "fecha_fallo_desde": start.strftime("%y-%m-%d"), "fecha_fallo_desde_aux": start.strftime("%d/%m/%Y"),
            "fecha_fallo_hasta": end.strftime("%y-%m-%d"), "fecha_fallo_hasta_aux": end.strftime("%d/%m/%Y"),
            "caratula": caratula, "firmantes": "", "expediente": expediente,
        }
        empty_seen = 0
        for attempt in range(SEARCH_ATTEMPTS):
            time.sleep(SEARCH_COOLDOWN + 10 * self.fails + 10 * attempt)
            with _client() as c:
                try:
                    _get(c, "GET", f"{BASE}/inicio.html")
                    time.sleep(REQUEST_DELAY)
                    image = _get(c, "GET", f"{BASE}/lib/securimage/securimage_show.php").content
                    code = self.solver.solve(image)
                    if not code:
                        continue
                    time.sleep(REQUEST_DELAY)
                    page = _get(c, "POST", f"{BASE}/inicio.html", data={**form, "captcha_code": code}).text
                    self.searches += 1

                    total = parse_total(page)
                    if total is None:          # form came back: captcha rejected
                        self.fails += 1
                        log(f"  captcha rejected (attempt {attempt + 1})")
                        continue
                    if total == 0:
                        empty_seen += 1
                        if empty_seen < 2:     # confirm once: an empty page can be a hiccup
                            continue
                        self.fails = 0
                        return 0, []

                    results = {r["uuid"] or r["expediente"]: r for r in parse_results(page)}
                    wanted = min(total, CAP)
                    for n in range(1, CAP // PAGE_SIZE):
                        if len(results) >= wanted:
                            break
                        time.sleep(REQUEST_DELAY)
                        page = _get(c, "POST", f"{BASE}/inicio.html", data={
                            **form, "captcha_code": code, "pagina": str(n), "token": parse_token(page),
                        }).text
                        batch = parse_results(page)
                        if not batch:
                            break
                        results.update({r["uuid"] or r["expediente"]: r for r in batch})
                    if len(results) < wanted:
                        log(f"  only {len(results)} of {wanted} expected results came back")
                    self.fails = 0
                    return total, list(results.values())
                except (httpx.TransportError, httpx.HTTPStatusError) as e:
                    self.fails += 1
                    log(f"  search error (attempt {attempt + 1}): {type(e).__name__}")
        raise RuntimeError(f"search failed {SEARCH_ATTEMPTS} times: {jurisdiccion} {oficina or camara} {start}..{end}")


def extract_pdf_text(pdf: bytes) -> str:
    import pymupdf
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc).strip()


# -- Scraper ------------------------------------------------------------------------

class PJNScraper:
    def __init__(self, catalog: Catalog, site: PJNSite, limit: int):
        self.cat = catalog
        self.site = site
        self.limit = limit
        self.new = 0
        self.refreshed = 0
        self.errors = 0
        self.status: dict[str, int] = {}
        self.pdf_client = _client()

    def _store(self, result: dict, jurisdiccion: str, tipo: str, key: str = "") -> None:
        source_id = result["uuid"] or result["expediente"]
        meta = {
            "source": SOURCE, "source_id": source_id, "url": result["pdf_url"],
            "tribunal": result["tribunal"], "expediente": result["expediente"],
            "caratula": result["caratula"], "fecha": result["fecha"],
            "jurisdiccion": JURISDICCIONES.get(jurisdiccion, jurisdiccion), "tipo_fallo": tipo,
        }
        if self.cat.has(SOURCE, source_id):
            self.cat.upsert(meta)
            self.cat.clear_failure(SOURCE, source_id)
            self.refreshed += 1
            return
        try:
            raw = extract_pdf_text(_get(self.pdf_client, "GET", result["pdf_url"]).content)
        except Exception as e:
            self.errors += 1
            self.cat.record_failure(SOURCE, source_id, url=result["pdf_url"], key=key, reason=type(e).__name__)
            log(f"  PDF failed {result['expediente']}: {type(e).__name__}: {str(e)[:80]}")
            return
        finally:
            time.sleep(REQUEST_DELAY)     # also after a failure: empty PDFs come in bursts
        firmantes, fecha_firma = quality.extract_firmantes(raw)
        status = self.cat.upsert({
            **meta,
            "texto": quality.clean_pjn_text(raw),
            "firmantes": firmantes,
            "fecha": meta["fecha"] or fecha_firma,
        })
        self.cat.clear_failure(SOURCE, source_id)
        self.status[status] = self.status.get(status, 0) + 1
        self.new += 1

    def run(self, jurisdiccion: str, camara: str, tipo: str, start: date, end: date) -> None:
        # Newest first, one year at a time; crawl splits by date when a range exceeds CAP.
        for year in range(end.year, start.year - 1, -1):
            y_start, y_end = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
            for rec in self._crawl(jurisdiccion, camara, "", tipo, y_start, y_end):
                if rec.truncated:
                    self._split_by_oficina(jurisdiccion, camara, tipo, rec)
                if self.new >= self.limit:
                    return

    def _split_by_oficina(self, jurisdiccion: str, camara: str, tipo: str, rec) -> None:
        """A single day over CAP: one search per tipo de oficina (Salas, then juzgados, …).

        Only a group that is itself over CAP is split office by office. Verified live on
        2026-03-31: Salas 387 + juzgados 83 = 470, the cámara-level total. Stops as soon as
        the groups cover the day; falls back to every oficina if they never do.
        """
        log(f"  {rec.start}: {rec.total} > {CAP}, splitting by tipo de oficina")
        covered = 0
        for tipo_oficina in OFICINA_TIPOS:
            if covered >= rec.total or self.new >= self.limit:
                break
            covered += self._group(jurisdiccion, camara, tipo, tipo_oficina, rec.start, rec.end)
        if covered < rec.total and self.new < self.limit:
            log(f"  {rec.start}: tipos de oficina cover {covered} of {rec.total}, searching every oficina")
            covered = 0
            for oficina, _ in self.site.oficinas(camara):
                if covered >= rec.total or self.new >= self.limit:
                    break
                covered += self._office_day(jurisdiccion, camara, tipo, oficina, rec.start, rec.end)
        if covered < rec.total:
            log(f"  {rec.start}: oficinas cover {covered} of {rec.total}")

    def _group(self, jurisdiccion: str, camara: str, tipo: str, tipo_oficina: str, start: date, end: date) -> int:
        """Search one tipo de oficina for the day; split it office by office only if it is over CAP."""
        for rec in self._crawl(jurisdiccion, camara, "", tipo, start, end, tipo_oficina):
            if rec.truncated:
                # Stop as soon as the offices searched add up to the group total: each extra office is a
                # captcha and a search (2026-08-03, seguridad social: 2 of 5 Salas held all 117).
                covered = 0
                for oficina, _ in self.site.oficinas(camara, tipo_oficina):
                    if covered >= rec.total or self.new >= self.limit:
                        break
                    done = self._key(jurisdiccion, camara, oficina, tipo, rec.start, rec.end)
                    if self.cat.search_done(SOURCE, done):          # resumed run: count it, don't repeat it
                        covered += self.cat.search_total(SOURCE, done)
                        continue
                    covered += self._office_day(jurisdiccion, camara, tipo, oficina, rec.start, rec.end)
        return self.cat.search_total(SOURCE, self._key(jurisdiccion, camara, "", tipo, start, end, tipo_oficina))

    def _office_day(self, jurisdiccion: str, camara: str, tipo: str, oficina: str, start: date, end: date) -> int:
        """One oficina for one day; if even that is over CAP, split it by the year in the case number.

        Returns what the site reported for that oficina and day.
        """
        for rec in self._crawl(jurisdiccion, camara, oficina, tipo, start, end):
            if rec.truncated and rec.start == rec.end:
                self._split_by_year(jurisdiccion, camara, tipo, oficina, rec)
        return self.cat.search_total(SOURCE, self._key(jurisdiccion, camara, oficina, tipo, start, end))

    def _split_by_year(self, jurisdiccion: str, camara: str, tipo: str, oficina: str, rec) -> None:
        """An oficina with more than CAP rulings in a single day (seguridad social, Sala 1: 147 on 2026-08-04).

        The site's expediente field matches part of the case number, so "/2021" returns only the 2021
        cases: one search per year, newest first, until the years add up to the day's total.
        """
        log(f"  {oficina} {rec.start}: {rec.total} > {CAP}, splitting by expediente year")
        # The first CAP results already show which case years are common: search those first (most frequent
        # first), then the unseen years newest first. The few rulings left out are almost always in a seen
        # year, so the total is covered in a handful of searches instead of walking back year by year
        # (2025-09-29, Sala 1: 19 searches to cover 106 rulings).
        seen = Counter(int(m.group(1)) for r in rec.results for m in [re.search(r"/(\d{4})\b", r["expediente"] or "")] if m)
        order = [y for y, _ in seen.most_common()]
        order += [y for y in range(rec.end.year, EXPEDIENTE_FIRST_YEAR - 1, -1) if y not in seen]
        covered = 0
        for year in order:
            if covered >= rec.total or self.new >= self.limit:
                break
            expediente = f"/{year}"
            done = self._key(jurisdiccion, camara, oficina, tipo, rec.start, rec.end, expediente=expediente)
            if self.cat.search_done(SOURCE, done):
                covered += self.cat.search_total(SOURCE, done)
                continue
            for leaf in self._crawl(jurisdiccion, camara, oficina, tipo, rec.start, rec.end, expediente=expediente):
                if not leaf.split:
                    covered += leaf.total
        if covered < rec.total:
            log(f"  {oficina} {rec.start}: expediente years cover {covered} of {rec.total}")

    @staticmethod
    def _key(jurisdiccion: str, camara: str, oficina: str, tipo: str, s: date, e: date, tipo_oficina: str = "",
             expediente: str = "") -> str:
        where = (oficina or (f"*{tipo_oficina}" if tipo_oficina else "*")) + expediente
        return f"{jurisdiccion}|{camara}|{where}|{tipo}|{s}|{e}"

    def _crawl(self, jurisdiccion: str, camara: str, oficina: str, tipo: str, start: date, end: date,
               tipo_oficina: str = "", expediente: str = ""):
        def key(s: date, e: date) -> str:
            return self._key(jurisdiccion, camara, oficina, tipo, s, e, tipo_oficina, expediente)

        def search(s: date, e: date):
            return self.site.search(jurisdiccion, camara, oficina, tipo, s, e, tipo_oficina=tipo_oficina,
                                    expediente=expediente)

        for rec in crawl(search, start, end, skip=lambda s, e: self.cat.search_done(SOURCE, key(s, e))):
            if not rec.split:
                leaf = key(rec.start, rec.end)
                self.cat.record_listing(SOURCE, leaf, [r["uuid"] or r["expediente"] for r in rec.results])
                for result in rec.results:
                    if self.new >= self.limit:
                        return
                    self._store(result, jurisdiccion, tipo, key=leaf)
            self.cat.record_search(SOURCE, key(rec.start, rec.end), total=rec.total,
                                   fetched=0 if rec.split else len(rec.results),
                                   split=rec.split, truncated=rec.truncated)
            label = "split" if rec.split else f"{len(rec.results)} results" + (" TRUNCATED" if rec.truncated else "")
            where = oficina or (f"{camara}/tipo {tipo_oficina}" if tipo_oficina else camara)
            log(f"{where} {rec.start}..{rec.end}: site total {rec.total:,} -> {label} | "
                f"new {self.new:,} refreshed {self.refreshed:,} err {self.errors} | "
                f"{self.status} | captcha ${self.site.solver.cost:.4f}")
            yield rec

def site_total(solver: "CaptchaSolver", camara: str, tipo: str, start: date, end: date,
               jurisdiccion: str = "5-5") -> int | None:
    """What the site reports for a whole range, from the first page of one search (no PDFs, no paging)."""
    form = {
        "acc": "searchFallos", "tipo": "fallo", "paginado": "1", "pagina": "0", "token": "",
        "jurisdiccion": jurisdiccion, "camara_id": camara, "tribunal_id": "", "tid": camara, "tipo_oficina_id": "",
        "tipofallo": tipo,
        "fecha_fallo_desde": start.strftime("%y-%m-%d"), "fecha_fallo_desde_aux": start.strftime("%d/%m/%Y"),
        "fecha_fallo_hasta": end.strftime("%y-%m-%d"), "fecha_fallo_hasta_aux": end.strftime("%d/%m/%Y"),
        "caratula": "", "firmantes": "", "expediente": "",
    }
    for attempt in range(3):
        time.sleep(SEARCH_COOLDOWN * attempt)
        with _client() as c:
            _get(c, "GET", f"{BASE}/inicio.html")
            time.sleep(REQUEST_DELAY)
            code = solver.solve(_get(c, "GET", f"{BASE}/lib/securimage/securimage_show.php").content)
            time.sleep(REQUEST_DELAY)
            if code:
                total = parse_total(_get(c, "POST", f"{BASE}/inicio.html", data={**form, "captcha_code": code}).text)
                if total is not None:
                    return total
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="PJN sentencias → catalog")
    parser.add_argument("--jurisdiccion", action="append", help="Code such as 5-5 (repeatable). Default: all")
    parser.add_argument("--camara", action="append", help="Cámara id such as C_7 (repeatable). Default: all")
    parser.add_argument("--tipo", default="D", choices=list(TIPOS), help="Default: D (definitivas)")
    parser.add_argument("--desde", type=date.fromisoformat, default=FIRST_DATE)
    parser.add_argument("--hasta", type=date.fromisoformat, default=date.today())
    parser.add_argument("--limit", type=int, default=10_000_000, help="Max new documents")
    parser.add_argument("--list-camaras", metavar="JURISDICCION")
    args = parser.parse_args()

    import anthropic
    try:
        _scrape(args)
    except tuple(getattr(anthropic, name) for name in FATAL_API_ERRORS) as e:
        sys.exit(f"Anthropic API rejected the request ({type(e).__name__}): {e}\n"
                 "Check ANTHROPIC_API_KEY (and ANTHROPIC_WORKSPACE_ID if the key has no workspace) in backend/.env.")


def _scrape(args: argparse.Namespace) -> None:
    site = PJNSite(CaptchaSolver())
    if args.list_camaras:
        for cid, name in site.camaras(args.list_camaras):
            print(f"{cid:<10} {name}")
        return

    cat = Catalog(settings.data_root / "catalog.db")
    scraper = PJNScraper(cat, site, args.limit)
    try:
        for jur in args.jurisdiccion or list(JURISDICCIONES):
            camaras = [(c, c) for c in args.camara] if args.camara else site.camaras(jur)
            log(f"== {JURISDICCIONES.get(jur, jur)}: {len(camaras)} cámaras, tipo {TIPOS[args.tipo]}")
            for cid, name in camaras:
                if scraper.new >= args.limit:
                    break
                log(f"-- {name}")
                try:
                    scraper.run(jur, cid, args.tipo, args.desde, args.hasta)
                except RuntimeError as e:
                    scraper.errors += 1
                    log(f"  SKIP {name}: {e}")
    finally:
        cat.close()
        log(f"DONE new {scraper.new:,} refreshed {scraper.refreshed:,} errors {scraper.errors} "
            f"searches {site.searches} captcha ${site.solver.cost:.4f} | {scraper.status}")
        log("Next: python -m scripts.audit")


if __name__ == "__main__":
    main()
