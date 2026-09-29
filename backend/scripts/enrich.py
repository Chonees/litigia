"""Enrichment at ingest, $0 (regex only): the fields a litigator reads before anything else.

- objeto:      what the case is about, from the carátula ("s/ DESPIDO")
- resultado:   what the court decided, from the resolutive part (not the first-instance ruling it describes)
- normas:      cited laws and LCT articles, normalized ("ley 27.348", "LCT art. 80")
- numero:      "SD 115.631" / "SI 12.345", the number lawyers cite
- votos:       judges who voted, in order ("X dijo:")
- por_mayoria: the resolutive part says the decision was by majority (there was a different vote)

Dissent is NOT detected from words like "disiento": in CNAT rulings they usually quote the
first-instance judge or reject a party's "mera disidencia". "por mayoría" in the resolutive
part is the reliable signal.
"""

import re

# Cámara: "el Tribunal RESUELVE" · first instance: "FALLO:" (uppercase with colon) or "RESUELVO"
RESOLUTIVE = re.compile(r"RESUELVE|RESOLVER|SE\s+RESUELVE|FALLA\b|RESUELVO|(?-i:FALLO\s*:)", re.IGNORECASE)
MAYORIA_WINDOW = 150

RESULTADOS = [
    ("confirma", r"\bconfirm(?:ar|ase|a|ando)\b"),
    ("revoca", r"\brevoc(?:ar|ase|a|ando)\b|\bdejar\s+sin\s+efecto\b|\bd[ée]jase\s+sin\s+efecto\b"),
    ("modifica", r"\bmodific(?:ar|ase|a|ando)\b"),
    ("rechaza", r"\bdesestim(?:ar|ase|a)\b|\brechaz(?:ar|ase|a)\b|\bmal\s+concedid[oa]\b"),
    ("hace lugar", r"\bhacer\s+lugar\b|\bhaciendo\s+lugar\b|\bh[áa]gase\s+lugar\b|\bcondenar\b|\bcondeno\b"),
    ("abstracto", r"\babstract[oa]\b"),
    ("desierto", r"\bdesiert[oa]\b"),
    ("nulidad", r"\bnulidad\b"),
]

LEY = re.compile(r"\bley(?:es)?\s*(?:n[°º.]*\s*)?(\d{1,2})\.?(\d{3})\b", re.IGNORECASE)
LCT = re.compile(
    r"\bart(?:[íi]culo|s?\.)\s*(\d+)[^.;\n]{0,20}?(?:LCT|L\.C\.T|Ley de Contrato de Trabajo)",
    re.IGNORECASE,
)
# "SENTENCIA DEFINITIVA Nº 115.631" (Cámara) or "SENTENCIA NÚMERO: 18867" (first instance, a sentencia definitiva).
# The number must not be followed by "/": "SENTENCIA CNAT NÚMERO: 31748/2021" is a case number.
NUMERO = re.compile(
    r"SENTENCIA\s+(?:(DEFINITIVA|INTERLOCUTORIA)\s+)?(?:N[°º]|NRO\.?|N[ÚU]MERO)\s*[.:]?\s*(\d[\d.]*\d)(?![\d.]*\s*/)",
    re.IGNORECASE,
)
# Each vote opens with "El doctor X dijo:"; variants seen: "manifestó:", "X, dijo:", and "dijo Por…" without
# the colon. Without the colon the next word must be capitalized, so "el Dr. Pérez dijo que…" (a quote) is not a vote.
VOTO = re.compile(
    r"\b(?:el|la)\s+(?:doctor|doctora|dr\.?|dra\.?)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.\s]{2,60}?),?\s+"
    r"(?:dijo|manifest[óo])(?:\s*:|(?-i:(?=\s+[A-ZÁÉÍÓÚÑ])))",
    re.IGNORECASE,
)


def detect_instancia(tribunal: str) -> str:
    """camara / primera / corte, from the tribunal name ("" when unknown)."""
    name = tribunal.upper().replace("Á", "A")
    if "CORTE SUPREMA" in name:
        return "corte"
    if "JUZGADO" in name:
        return "primera"
    if "CAMARA" in name:
        return "camara"
    return ""


def extract_objeto(caratula: str) -> str:
    m = re.search(r"\bs/\s*(.+)$", caratula or "", re.IGNORECASE)
    return re.sub(r"\s+", " ", m.group(1)).strip().upper() if m else ""


def _resolutive(texto: str) -> tuple[str, int]:
    """Text after the LAST resolutive marker, and where that marker starts (-1 if none)."""
    last = None
    for last in RESOLUTIVE.finditer(texto):
        pass
    return (texto[last.end():], last.start()) if last else ("", -1)


def extract_resultado(texto: str) -> str:
    section, _ = _resolutive(texto)
    if not section:
        return ""
    found = []
    for name, pattern in RESULTADOS:
        m = re.search(pattern, section, re.IGNORECASE)
        if m:
            found.append((m.start(), name))
    return min(found)[1] if found else ""


def por_mayoria(texto: str) -> bool:
    section, start = _resolutive(texto)
    if start < 0:
        return False
    window = texto[max(0, start - MAYORIA_WINDOW):start] + section
    return bool(re.search(r"por\s+mayor[íi]a", window, re.IGNORECASE))


def extract_normas(texto: str) -> list[str]:
    normas = {f"ley {a}.{b}" for a, b in LEY.findall(texto)}
    normas |= {f"LCT art. {n}" for n in LCT.findall(texto)}
    return sorted(normas)


def extract_numero(texto: str) -> str:
    m = NUMERO.search(texto[:800])
    if not m:
        return ""
    kind = (m.group(1) or "DEFINITIVA").upper()      # first-instance "SENTENCIA NÚMERO" is a definitiva
    return ("SI " if kind.startswith("I") else "SD ") + m.group(2)


def _name(raw: str) -> str:
    words = re.sub(r"\s+", " ", raw).strip().split(" ")
    return " ".join(w.capitalize() if w.isupper() and len(w) > 2 else w for w in words)


def extract_votos(texto: str) -> list[str]:
    votos: list[str] = []
    for raw in VOTO.findall(texto):
        name = _name(raw)
        if name not in votos:
            votos.append(name)
    return votos


EXPEDIENTE_TEXTO = re.compile(
    r"(?:EXPEDIENTE|EXPTE|CAUSA)\.?\s*(?:N[°º]|NRO\.?|N[ÚU]MERO)?\s*[.:]?\s*(?:[A-Z]{2,4}\s*)?"
    r"(\d{1,3}(?:\.\d{3})+|\d+)\s*/\s*(\d{4}|\d{2})\b",
    re.IGNORECASE,
)


def extract_expediente_texto(texto: str) -> str:
    """The case number as the ruling writes it in its heading ("46676/2016", "19528/18"); "" if absent."""
    m = EXPEDIENTE_TEXTO.search(texto[:800])
    return f"{int(m.group(1).replace('.', ''))}/{m.group(2)}" if m else ""


def enrich(doc: dict) -> dict:
    texto = doc.get("texto") or ""
    return {
        "objeto": extract_objeto(doc.get("caratula") or ""),
        "resultado": extract_resultado(texto),
        "normas": extract_normas(texto),
        "numero": extract_numero(texto),
        "expediente_texto": extract_expediente_texto(texto),
        "votos": extract_votos(texto),
        "por_mayoria": por_mayoria(texto),
    }
