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
import unicodedata

# Cámara: "el Tribunal RESUELVE", "el Tribunal decide:" (Civil) · first instance: "FALLO:" or "Fallo:" (never
# lowercase, which is "the ruling:"), "RESUELVO", "DECIDO:". "Costas … en atención a la forma que se resuelve"
# (CFSS, CNAT) sits inside the resolutive part and must not restart it.
# CNCom: "los señores Jueces de Cámara acuerdan:". CNCiv first instance: the PDF often drops the bold "FALLO",
# leaving "Por todo lo expuesto, :" / "…citadas, :", or the lead-in goes straight to the verb ("…citadas,
# Rechazando la demanda", "juzgando, en definitiva, Haciendo lugar"). "resolver" counts only as "RESOLVER:":
# the CNACAF closes with notes like "…en condiciones de resolver conforme el art. 109 del RJN".
LEAD_IN = r"(?:expuesto|citad[oa]s|en\s+definitiva|consideraciones)\s*[,;]"
RESOLUTIVE = re.compile(
    r"(?<!que se )(?<!que )"
    r"(?:RESUELVE|RESOLVER\s*:|SE\s+RESUELVE|FALLA\b|RESUELVO|(?-i:F(?:ALLO|allo)\s*:)|\bdecide\s*:|\bdecido\s*:"
    r"|\bacuerdan\s*:|" + LEAD_IN + r"\s*:|" + LEAD_IN + r"(?=\s*(?-i:(?:Haciendo|Admitiendo|Rechazando|Condenando|Desestimando))\b))",
    re.IGNORECASE,
)
MAYORIA_WINDOW = 150

# Matched on the resolutive part folded to lowercase ASCII ("Confírmase" → "confirmase"). Verb forms seen in
# CNAT and CNCiv: infinitive, imperative + se, gerund (first instance) and subjunctive ("se la confirme").
# "confirmarla", "revocarlo": the infinitive with an enclitic pronoun (CFSS). First person ("hago lugar",
# "rechazo", "admito") is how first-instance judges of the seguridad social write. Rejecting a DEFENSE
# ("rechazo la defensa de prescripción") is not rejecting the claim, and neither is rejecting the counterclaim.
ENCLITIC = r"(?:la|lo|las|los)?"
NOT_A_DEFENSE = r"(?!\s+(?:la\s+|el\s+|las\s+|los\s+)?(?:defensa|excepci|planteo|prescripci|reconvenci))"
RESULTADOS = [
    ("confirma", rf"\bconfirm(?:ar{ENCLITIC}|ase|a|ando|e|en)\b"),
    ("revoca", rf"\brevo(?:c(?:ar{ENCLITIC}|ase|a|ando)|que|quen|quese)\b|\bdejar\s+sin\s+efecto\b|\bdejase\s+sin\s+efecto\b"),
    # Cámara Civil also modifies by raising or lowering amounts: "Elevar la suma reconocida…", "Reducir la indemnización…"
    ("modifica", rf"\bmodifi(?:c(?:ar{ENCLITIC}|ase|a|ando)|que|quen|quese)\b"
                 r"|\b(?:elev|increment|reduc|disminu)(?:ar|ir|ase|ese|ando|iendo|yendo)\b[^.;]{0,40}?"
                 r"\b(?:suma|monto|importe|cantidad|indemnizacion|partida|resarcimiento|condena|capital)"),
    ("rechaza", rf"\bdesestim(?:ar|ase|a|ando|o){NOT_A_DEFENSE}\b|\brecha(?:z(?:ar|ase|a|ando|o)|ce|cen|cese)\b{NOT_A_DEFENSE}"
                r"|\bmal\s+concedid[oa]\b|\bdeneg(?:ar|ase|a|o)\b|\bdeclarar\s+(?:formalmente\s+)?inadmisible\b"),
    # CNACAF: rulings that only decide which court hears the case
    ("competencia", r"\batribuir\s+la\s+competencia\b|\bdeclarar\s+la\s+(?:in)?competencia\b"
                    r"|\bdeclarar(?:se)?\s+(?:in)?competente\b"),
    ("hace lugar", r"\bhacer\s+(?:parcialmente\s+)?lugar\b|\bhaciendo\s+(?:parcialmente\s+)?lugar\b|\bhagase\s+lugar\b"
                   r"|\bhago\s+(?:parcialmente\s+)?lugar\b"
                   r"|\bcondenar\b|\bcondeno\b|\bcondenando\b"
                   r"|\badmit(?:ir|iendo|ase|o)\s+(?:parcialmente\s+)?la\s+demanda\b"
                   # ejecuciones fiscales and comercial "ejecutivo": ordering the enforcement to proceed
                   r"|\bmand(?:ar|ando|o)\s+(?:a\s+)?(?:llevar|seguir)\s+adelante\s+la\s+ejecucion\b"),
    ("abstracto", r"\babstract[oa]\b|\binoficios[oa]\b"),        # "declarar inoficioso pronunciarse"
    ("desierto", r"\bdesiert[oa]\b"),
    ("nulidad", r"\bnulidad\b"),
]

LEY = re.compile(r"\bley(?:es)?\s*(?:n[°º.]*\s*)?(\d{1,2})\.?(\d{3})\b", re.IGNORECASE)
LCT = re.compile(
    r"\bart(?:[íi]culo|s?\.)\s*(\d+)[^.;\n]{0,20}?(?:LCT|L\.C\.T|Ley de Contrato de Trabajo)",
    re.IGNORECASE,
)
# Civil and Commercial Code (2015) and the national procedural code, as the CNCiv cites them
CCYC = re.compile(
    r"\bart(?:[íi]culo|s?\.)\s*(\d+)[^.;\n]{0,25}?"
    r"(?:C[óo]digo\s+Civil\s+y\s+Comercial|CCyCN?\b|CCCN\b|C[óo]d\.\s*Civ\.\s*y\s*Com\.)",
    re.IGNORECASE,
)
CPCCN = re.compile(
    r"\bart(?:[íi]culo|s?\.)\s*(\d+)[^.;\n]{0,25}?(?:C[óo]digo\s+Procesal(?!\s+Penal)|CPCCN?\b)",
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
# The CNCiv titles the judge first: "el Juez de Cámara Doctor X dijo:", "la señora juez Doctora X dijo:".
VOTO = re.compile(
    r"\b(?:el|la)\s+(?:(?:se[ñn]or|se[ñn]ora|sr\.?|sra\.?)\s+)?(?:(?:juez|jueza|vocal)(?:\s+de\s+c[áa]mara)?,?\s+)?"
    r"(?:doctor|doctora|dr\.?|dra\.?)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.\s]{2,60}?),?\s+"
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


RESOLUTIVE_FROM = 0.4    # the resolutive part closes a ruling; a marker earlier than this is reasoning


SENTENCIO = re.compile(r"\bsentencio\s+(?:este|el\s+presente)\s+juicio\b", re.IGNORECASE)


def _resolutive(texto: str) -> tuple[str, int]:
    """Text after the LAST resolutive marker, and where that marker starts (-1 if none).

    Markers in the first 40% of the text are ignored: "corresponde resolver…" in the reasoning of a ruling
    that has no resolutive formula (seen in Juzgado Civil 95) must not pass for one.
    """
    last = None
    for m in RESOLUTIVE.finditer(texto, int(len(texto) * RESOLUTIVE_FROM)):
        last = m
    if not last:
        # short "ejecutivo" rulings decide up front: "sentencio este juicio de trance y remate, mandando llevar adelante…"
        last = SENTENCIO.search(texto)
    if not last:
        return "", -1
    section = texto[last.end():]
    # The PDF text sometimes prints the first item before the marker ("1) Revocar la sentencia En virtud de lo
    # expuesto, el Tribunal RESUELVE: apelada en lo que…"): when the part continues mid-sentence (lowercase),
    # bring back the "1)" that sits just before the marker.
    if re.match(r"[\s:.\-–|]*[a-záéíóúñ]", section):
        first = None
        for first in re.finditer(r"(?:^|\s)(?:1|I)\s*[.)\-–]+\s*(?=[A-ZÁÉÍÓÚ])", texto[max(0, last.start() - 250):last.start()]):
            pass
        if first:
            section = texto[max(0, last.start() - 250) + first.start():last.start()] + " " + section
    return section, last.start()


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


CLOSING = re.compile(r"\b(?:reg[ií]strese|notif[ií]quese|h[aá]gase\s+saber|dev[uú][eé]lvan?se)\b", re.IGNORECASE)
DECISION_WINDOW = 700     # how far before "Así se resuelve" / the closing formula the decision is looked for


def _first_result(section: str) -> str:
    section = _fold(section)
    found = []
    for name, pattern in RESULTADOS:
        m = re.search(pattern, section, re.IGNORECASE)
        if m:
            found.append((m.start(), name, m.end()))
    if not found:
        return ""
    _, name, end = min(found)
    # "Rechazar el recurso … y, en consecuencia, confirmar el pronunciamiento": what stands is a confirmation
    if name == "rechaza" and re.search(r"\bconfirm", re.split(r";|\s2\s*[.)]", section[end:end + 300])[0]):
        return "confirma"
    return name


def extract_resultado(texto: str) -> str:
    section, start = _resolutive(texto)
    result = _first_result(section) if section else ""
    if result:
        return result
    # The decision comes just before: "…corresponde confirmar la sentencia. Así se resuelve. Regístrese…" (CNACAF),
    # or the ruling has no resolutive formula at all and ends with "Regístrese, notifíquese".
    if start < 0:
        closing = CLOSING.search(texto, int(len(texto) * 0.7))
        if not closing:
            return ""
        start = closing.start()
    return _first_result(texto[max(0, start - DECISION_WINDOW):start])


def por_mayoria(texto: str) -> bool:
    section, start = _resolutive(texto)
    if start < 0:
        return False
    window = texto[max(0, start - MAYORIA_WINDOW):start] + section
    return bool(re.search(r"por\s+mayor[íi]a", window, re.IGNORECASE))


def extract_normas(texto: str) -> list[str]:
    normas = {f"ley {a}.{b}" for a, b in LEY.findall(texto)}
    normas |= {f"LCT art. {n}" for n in LCT.findall(texto)}
    normas |= {f"CCyC art. {n}" for n in CCYC.findall(texto)}
    normas |= {f"CPCCN art. {n}" for n in CPCCN.findall(texto)}
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


TITLE_INSIDE = re.compile(r"\b(?:doctor|doctora|dr|dra)\b\.?\s+", re.IGNORECASE)


def extract_votos(texto: str) -> list[str]:
    votos: list[str] = []
    for raw in VOTO.findall(texto):
        # "…voto de la Dra. Graciela L. Craig. LA Doctora Gabriela Vazquez dijo:" matches from the first title:
        # the judge voting is the one after the last title.
        raw = TITLE_INSIDE.split(raw)[-1]
        name = _name(raw)
        if name not in votos:
            votos.append(name)
    return votos


EXPEDIENTE_TEXTO = re.compile(
    r"(?:EXPEDIENTE|EXPTE|CAUSA)\.?\s*(?:N[°º]|NRO\.?|N[ÚU]MERO)?\s*[.:]?\s*(?:[A-Z]{2,4}\s*)?"
    r"(\d{1,3}(?:\.\d{3})+|\d+)\s*/\s*(\d{4}|\d{2})\b",
    re.IGNORECASE,
)


# The court's own number, with the PJN prefix of its fuero: "CAF 17946/2025/CA3", "CNT 46676/2016"
PJN_NUMBER = re.compile(r"\b(?:CAF|CNT|CIV|COM|CSS|CCF|CFP|CPE|CCC)\s*(\d{1,3}(?:\.\d{3})+|\d+)\s*/\s*(\d{4})\b")
# An agency's file inside the carátula ("DNM - EXPTE 3074/15 s/…") is not the court's case number
IN_CARATULA = re.compile(r"\s*s/", re.IGNORECASE)


def extract_expediente_texto(texto: str) -> str:
    """The case number as the ruling writes it in its heading ("46676/2016", "19528/18"); "" if absent."""
    head = texto[:800]
    m = PJN_NUMBER.search(head)
    if not m:
        m = next((x for x in EXPEDIENTE_TEXTO.finditer(head) if not IN_CARATULA.match(head, x.end())), None)
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
