"""Pure logic for the PJN scraper: results-page parsing and the adaptive crawl.

The site returns at most 100 results per search (5 pages of 20, paginated by
re-posting the form with the token it returns) but reports the real total.
`crawl` splits a date range until every piece fits under that cap, so we
collect everything instead of the first 100.
"""

import base64
import html as html_lib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Iterator

CAP = 100
PAGE_SIZE = 20

PDF_HREF = re.compile(r'href="([^"]*sentencia-[^"]+\.pdf[^"]*)"')
UUID = re.compile(r"sentencia-(?:SGU-)?([a-f0-9-]+)\.pdf")
INFO = re.compile(r"[?&](?:amp;)?info=([A-Za-z0-9_\-+/=%]+)")
LABEL = re.compile(r'<span class="s2">\s*([^<:]+):?\s*</span>\s*([^<]+)</li>')

INFO_KEYS = {
    "Tribunal": "tribunal",
    "Expediente N°": "expediente",
    "Carátula": "caratula",
    "Fecha de sentencia": "fecha",
}


def _iso(fecha: str) -> str:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", fecha.strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else fecha.strip()


def _decode_info(raw: str) -> dict:
    raw = raw.replace("%3D", "=")
    raw += "=" * (-len(raw) % 4)
    for decode in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return json.loads(decode(raw))
        except Exception:
            continue
    return {}


def _labels(block: str) -> dict:
    """Fallback when the viewer link is missing: read the visible label list."""
    found = {}
    for label, value in LABEL.findall(block):
        label = html_lib.unescape(label).strip()
        key = next((k for k in INFO_KEYS if k.split()[0] == label.split()[0]), None)
        if key:
            found[key] = html_lib.unescape(value).strip()
    return found


def parse_results(page: str) -> list[dict]:
    """One dict per result, with metadata taken from the same result block as its PDF."""
    results = []
    for block in page.split('<div class="result"')[1:]:
        pdf = PDF_HREF.search(block)
        if not pdf:
            continue
        pdf_url = html_lib.unescape(pdf.group(1))
        uuid = UUID.search(pdf_url)

        info = {}
        m = INFO.search(block)
        if m:
            info = _decode_info(m.group(1))
        if not info:
            info = _labels(block)

        meta = {name: re.sub(r"\s+", " ", str(info.get(key, ""))).strip() for key, name in INFO_KEYS.items()}
        meta["fecha"] = _iso(meta["fecha"])
        results.append({"pdf_url": pdf_url, "uuid": uuid.group(1) if uuid else "", **meta})
    return results


def parse_token(page: str) -> str:
    """Token the site expects when posting the form again for the next page."""
    m = re.search(r'document\.fallos\.token\.value\s*=\s*"([^"]+)"', page)
    return m.group(1) if m else ""


def parse_oficinas(options_html: str) -> list[tuple[str, str]]:
    """(tid, name) for each office (Sala, juzgado) under a cámara, from the ajax <option> list."""
    return [
        (tid, html_lib.unescape(name).strip())
        for tid, name in re.findall(r'<option value="([^"]+)"[^>]*>([^<]+)', options_html)
    ]


def parse_total(page: str) -> int | None:
    if "no ha arrojado" in page:
        return 0
    m = re.search(r"(\d[\d.]*)\s*resultado", page)
    return int(m.group(1).replace(".", "")) if m else None


# -- adaptive crawl -------------------------------------------------------------

@dataclass
class SearchRecord:
    start: date
    end: date
    total: int
    results: list = field(default_factory=list)
    split: bool = False       # too many results: children cover this range
    truncated: bool = False   # a single day still over the cap: we got only `CAP`


def _split(start: date, end: date, total: int, cap: int) -> list[tuple[date, date]]:
    days = (end - start).days + 1
    parts = max(2, min(days, math.ceil(total / (cap * 0.7))))
    ranges, cursor = [], start
    for i in range(parts):
        length = days // parts + (1 if i < days % parts else 0)
        stop = cursor + timedelta(days=length - 1)
        ranges.append((cursor, stop))
        cursor = stop + timedelta(days=1)
    return ranges


def crawl(
    search: Callable[[date, date], tuple[int, list]],
    start: date,
    end: date,
    cap: int = CAP,
    skip: Callable[[date, date], bool] | None = None,
) -> Iterator[SearchRecord]:
    """Search [start, end]; if the site reports more than `cap`, split and recurse.

    `skip(start, end)` lets the caller resume: ranges already fully collected are not searched.
    """
    if skip and skip(start, end):
        return
    total, results = search(start, end)
    days = (end - start).days + 1
    if total > cap and days > 1:
        yield SearchRecord(start, end, total, split=True)
        for s, e in _split(start, end, total, cap):
            yield from crawl(search, s, e, cap, skip)
    else:
        yield SearchRecord(start, end, total, results, truncated=total > cap)
