"""The data contract for LITIGIA: what a fallo needs to be useful for search.

A document is:
- indexable: meets every requirement, goes into the search index
- pending:   useful text but something recoverable is missing (metadata, OCR, paragraphs)
- rejected:  not worth indexing (too short, purely formal resolution, duplicate)

Rejection is a label with reasons, never a deletion: loosen a rule and re-assess
what is already in the catalog without scraping again.
"""

import hashlib
import re
import statistics
import unicodedata
from dataclasses import dataclass, field

MIN_CHARS = 800             # below this there is no reasoning to cite
BRIEF_CHARS = 1500          # under this a ruling is kept but flagged "breve"
FORMAL_MAX_CHARS = 4000     # formal patterns only reject short texts
MIN_LETTER_RATIO = 0.6      # below this the PDF is a scan without a text layer
MIN_PARAGRAPHS = 3          # needed to point at the holding paragraph

CONTRACT = {
    "min_chars": MIN_CHARS,
    "brief_chars": BRIEF_CHARS,
    "formal_max_chars": FORMAL_MAX_CHARS,
    "min_letter_ratio": MIN_LETTER_RATIO,
    "min_paragraphs": MIN_PARAGRAPHS,
    "required_metadata": ["fecha", "tribunal", "caratula"],
}

FORMAL = re.compile(
    r"art(?:\.|[íi]culo)\s*280"
    r"|desest[íi]mase\s+la\s+queja|se\s+desestima\s+la\s+queja"
    r"|t[ée]ngase\s+presente|decl[áa]rase\s+desiert"
    r"|es\s+inadmisible"
    r"|abstracta\s+la\s+cuesti[óo]n|cuesti[óo]n\s+abstracta"
    r"|desiert[oa]\s+el\s+recurso|declarar\s+desiert"
    # pure procedure: late appeals, deposits, withdrawals
    r"|interpuest[oa]\s+extempor[áa]neamente"
    r"|dep[óo]sito\s+previsto\s+en\s+el\s+art(?:\.|[íi]culo)\s*286"
    r"|t[ée]ngase(?:lo|la)?\s+por\s+desistid",
    re.IGNORECASE,
)

# Fees and orders to inform are formal only when they ARE the decision: rulings on the merits often narrate
# them ("el Tribunal dispuso como medida para mejor proveer…", CFSS retiro por invalidez). Looked for in the
# resolutive part when there is one, in the whole text otherwise (short decrees have no marker).
FORMAL_IF_DECIDED = re.compile(r"se\s+regulan\s+los\s+honorarios|medida\s+para\s+mejor\s+proveer", re.IGNORECASE)


# Rulings whose only object is a fee appeal, published as "definitivas" (CNACAF: ~6% of the fuero). They open
# with a fixed template, so only the opening is read: a ruling on the merits may use the phrase near its end.
FEES_ONLY = re.compile(r"mediante\s+la\s+regulaci[óo]n\s+de\s+honorarios\s+se\s+busca\s+compensar", re.IGNORECASE)
FEES_ONLY_OPENING = 1500


def is_formal(texto: str) -> bool:
    if FORMAL.search(texto):
        return True
    from scripts.enrich import _resolutive
    section, start = _resolutive(texto)
    return bool(FORMAL_IF_DECIDED.search(section if start >= 0 else texto))


TIPO_INTERLOCUTORIA = re.compile(r"SENT(?:ENCIA)?\.?\s*INT(?:ERLOCUTORIA)?\b", re.IGNORECASE)
TIPO_DEFINITIVA = re.compile(r"SENT(?:ENCIA)?\.?\s*DEF(?:INITIVA)?\b", re.IGNORECASE)


def detect_tipo(texto: str) -> str:
    """'D' or 'I' as the ruling labels itself in its heading; '' when it does not say."""
    head = texto[:800]
    if TIPO_INTERLOCUTORIA.search(head):
        return "I"
    if TIPO_DEFINITIVA.search(head):
        return "D"
    return ""

# -- PDF text cleanup -------------------------------------------------------

PAGE_HASH = re.compile(r"^#\d+#\d+#\d+\s*$")
SIGNATURE_LINE = re.compile(r"^(Fecha de firma:|Alta en sistema:|Firmado.*por:)", re.IGNORECASE)
SECTION_START = re.compile(
    r"^(?:(?:[IVXL]{1,6}|\d{1,2})\s*(?:\.-|\.|-|\))|[a-z]\)"
    r"|Y?\s*VISTOS|CONSIDERANDO|RESULTANDO|FUNDAMENTOS|SE RESUELVE|RESUELVE|POR ELLO)",
)
TERMINAL = re.compile(r"[.:;][\"”»)]?\s*-?\s*$")
HEADER_WINDOW = 6


def _norm_line(line: str) -> str:
    return re.sub(r"[ \t ]+", " ", line).strip()


def _pages(lines: list[str]) -> list[list[str]]:
    pages, current = [], []
    for line in lines:
        if PAGE_HASH.match(line.strip()):
            if current:
                pages.append(current)
            current = []
        else:
            current.append(line)
    if current:
        pages.append(current)
    return pages


def _header_lines(pages: list[list[str]]) -> set[str]:
    """Short lines that repeat at the top of several pages (court name, etc.)."""
    seen: dict[str, int] = {}
    for page in pages:
        top = {l for l in (_norm_line(x) for x in page[:HEADER_WINDOW]) if l and len(l) < 150}
        for line in top:
            seen[line] = seen.get(line, 0) + 1
    headers = {line for line, n in seen.items() if n >= 2}
    headers.add("Poder Judicial de la Nación")
    return headers


def clean_pjn_text(raw: str) -> str:
    """Strip page stamps, signatures and headers; rebuild paragraphs split by the PDF.

    Paragraphs are separated by a blank line in the result.
    """
    pages = _pages(raw.split("\n"))
    headers = _header_lines(pages)

    lines: list[str] = []
    for page in pages:
        for i, line in enumerate(page):
            norm = _norm_line(line)
            if SIGNATURE_LINE.match(norm):
                continue
            if i < HEADER_WINDOW and norm in headers:
                continue
            lines.append(norm)

    widths = [len(l) for l in lines if len(l) > 20]
    typical = statistics.median(widths) if widths else 70

    paragraphs: list[str] = []
    current = ""
    prev = ""
    for line in lines:
        if not line:
            if current:
                paragraphs.append(current)
            current, prev = "", ""
            continue
        breaks = bool(current) and (
            SECTION_START.match(line)
            or (TERMINAL.search(prev) and len(prev) < 0.75 * typical)
        )
        if breaks:
            paragraphs.append(current)
            current = line
        elif current.endswith("-") and current[-2:-1].isalpha() and line[:1].islower():
            current = current[:-1] + line
        else:
            current = f"{current} {line}" if current else line
        prev = line
    if current:
        paragraphs.append(current)
    return strip_noise_paragraphs("\n\n".join(p.strip() for p in paragraphs if p.strip()))


NOISE_PARAGRAPH = re.compile(r"[\d\s.,:;\-–—()/]*")
NOISE_MAX_CHARS = 8     # page-number sized; longer numeric paragraphs are tables (amounts, IBM, liquidations)


def strip_noise_paragraphs(text: str) -> str:
    """Drop paragraphs that are only page numbers or punctuation ("2", ":", "- 3 -")."""
    return "\n\n".join(p for p in split_paragraphs(text)
                       if not (len(p) <= NOISE_MAX_CHARS and NOISE_PARAGRAPH.fullmatch(p)))


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


JUDGE_ROLE = re.compile(r"JUEZ|PRESIDENT|VOCAL", re.IGNORECASE)


def extract_firmantes(raw: str) -> tuple[list[str], str]:
    """Judges who signed (not secretaries) and the latest signature date (ISO)."""
    firmantes: list[str] = []
    for name, role in re.findall(r"^Firmado por:\s*([^,\n]+),\s*([^\n]*)", raw, re.MULTILINE):
        name = name.strip()
        if JUDGE_ROLE.search(role) and name not in firmantes:
            firmantes.append(name)
    dates = [f"{y}-{m}-{d}" for d, m, y in re.findall(r"Fecha de firma:\s*(\d{2})/(\d{2})/(\d{4})", raw)]
    return firmantes, max(dates) if dates else ""


# -- metadata ---------------------------------------------------------------

HEADER_TRIBUNAL = re.compile(r"^\s*(C[ÁA]MARA\b[^\n]{3,120}?)\s*$", re.IGNORECASE)


def extract_tribunal(raw: str) -> str:
    """Court name from a page header line; signatures ('JUEZ DE CAMARA') don't count."""
    for page in _pages(raw.split("\n")):
        for line in page[:HEADER_WINDOW]:
            m = HEADER_TRIBUNAL.match(_norm_line(line))
            if m:
                return m.group(1)
    return ""


FUEROS = [
    ("CORTE SUPREMA", "corte suprema"),
    ("SEGURIDAD SOCIAL", "seguridad social"),
    ("CIVIL Y COMERCIAL FEDERAL", "civil y comercial federal"),
    ("CONTENCIOSO ADMINISTRATIVO", "contencioso administrativo federal"),
    ("EJECUCIONES FISCALES", "contencioso administrativo federal"),   # juzgados under the CNACAF
    ("PENAL ECONOMICO", "penal economico"),
    ("CASACION PENAL", "penal"),
    ("CRIMINAL", "penal"),
    ("PENAL", "penal"),
    ("TRABAJO", "laboral"),
    ("COMERCIAL", "comercial"),
    ("CIVIL", "civil"),
    ("ELECTORAL", "electoral"),
    ("FEDERAL", "federal"),
]


def _ascii_upper(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def detect_fuero(tribunal: str) -> str:
    if not tribunal.strip():
        return ""
    name = _ascii_upper(tribunal)
    for needle, fuero in FUEROS:
        if needle in name:
            return fuero
    return "otro"


def text_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(norm.encode()).hexdigest()[:32]


# -- the contract -----------------------------------------------------------

@dataclass
class Assessment:
    status: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _letter_ratio(text: str) -> float:
    chars = [c for c in text if not c.isspace()]
    return sum(c.isalpha() for c in chars) / len(chars) if chars else 0.0


def expediente_mismatch(sistema: str, texto: str) -> bool:
    """The PJN system number and the one written in the ruling differ (a typo on either side)."""
    a = re.search(r"(\d+)/(\d{4})", sistema)
    b = re.search(r"(\d+)/(\d{2,4})", texto)
    if not a or not b:
        return False
    same_year = b.group(2) == a.group(2) or b.group(2) == a.group(2)[2:]
    return not (int(a.group(1)) == int(b.group(1)) and same_year)


def assess(doc: dict) -> Assessment:
    texto = doc.get("texto") or ""
    reject: list[str] = []
    pending: list[str] = []
    warnings: list[str] = []

    if len(texto) < MIN_CHARS:
        reject.append("texto_corto")
    elif _letter_ratio(texto) < MIN_LETTER_RATIO:
        pending.append("necesita_ocr")
    if len(texto) < FORMAL_MAX_CHARS and is_formal(texto):
        reject.append("resolucion_formal")
    if FEES_ONLY.search(texto[:FEES_ONLY_OPENING]):
        reject.append("solo_honorarios")

    tribunal = doc.get("tribunal") or ""
    caratula = doc.get("caratula") or ""
    if not doc.get("fecha"):
        pending.append("sin_fecha")
    if not tribunal:
        pending.append("sin_tribunal")
    if not caratula or caratula == doc.get("expediente"):
        pending.append("sin_caratula")
    if texto and "necesita_ocr" not in pending and len(split_paragraphs(texto)) < MIN_PARAGRAPHS:
        pending.append("sin_parrafos")

    if MIN_CHARS <= len(texto) < BRIEF_CHARS:
        warnings.append("breve")
    if expediente_mismatch(doc.get("expediente") or "", doc.get("expediente_texto") or ""):
        warnings.append("expediente_no_coincide")
    tipo_texto = detect_tipo(texto)
    if doc.get("tipo_fallo") and tipo_texto and tipo_texto != doc["tipo_fallo"]:
        warnings.append("tipo_no_coincide")
    if (tribunal and "SALA" not in _ascii_upper(tribunal) and "JUZGADO" not in _ascii_upper(tribunal)
            and detect_fuero(tribunal) != "corte suprema"):
        warnings.append("sin_sala")
    if tribunal and detect_fuero(tribunal) == "otro":
        warnings.append("fuero_desconocido")
    if not doc.get("expediente"):
        warnings.append("sin_expediente")

    if reject:
        return Assessment("rejected", reject + pending, warnings)
    if pending:
        return Assessment("pending", pending, warnings)
    return Assessment("indexable", [], warnings)
