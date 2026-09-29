"""Vote structure of a Cámara ruling, computed in code.

Each vote opens with "EL DOCTOR X DIJO:" / "LA DOCTORA X DIJO:". When the judges disagree,
the third one writes "…materia de disidencia entre mis colegas, adhiero al voto de la Dra. X":
that is the majority. Knowing the majority in code removes the hardest indirection from the
paragraph-role question (a labeler cannot tell majority from dissent without the outcome).
"""

import re

from scripts.enrich import RESULTADOS

JUDGE = r"(?:EL|LA)\s+(?:DOCTORA?|DRA?\.)\s+"
# The name stops at the next "EL DOCTOR / LA DRA." so "…de la Dra. X. LA DOCTORA Y DIJO:" yields Y.
DIJO = re.compile(JUDGE + r"((?:(?!" + JUDGE + r").)+?),?\s+(?:DIJO|MANIFEST[ÓO])(?:\s*:|(?-i:(?=\s+[A-ZÁÉÍÓÚÑ])))",
                  re.IGNORECASE)
RESOLUTIVE = re.compile(r"RESUELVE|acuerdo que antecede", re.IGNORECASE)
DISSENT = re.compile(
    r"\bdisiento\b|\ben disidencia\b|materia de (?:disidencia|controversia) entre mis colegas"
    r"|no comparto (?:la soluci|el voto)",
    re.IGNORECASE,
)
JOINS = re.compile(r"adhiero al voto (?:de la|del)\s+(?:Dra?\.|Doctora?)\s+(?:[A-ZÁÉÍÓÚÑ]\.\s*)*([A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ-]+)",
                   re.IGNORECASE)


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip(" .,:")


def detect_votes(paragraphs: list[str]) -> dict:
    starts = []   # (paragraph index where the vote begins, judge)
    for i, p in enumerate(paragraphs):
        for m in DIJO.finditer(p):
            text_before = p[: m.start()].strip()
            starts.append((i + 1 if text_before else i, _clean(m.group(1))))
    if not starts:
        return {"votos": [], "hay_disidencia": False, "voto_mayoria": "", "votos_minoria": []}

    end = len(paragraphs)
    for i in range(starts[-1][0], len(paragraphs)):
        if RESOLUTIVE.search(paragraphs[i]):
            end = i
            break
    votes = []
    for k, (start, judge) in enumerate(starts):
        stop = starts[k + 1][0] if k + 1 < len(starts) else end
        votes.append({"juez": judge, "parrafos": [f"p{i}" for i in range(start, stop)]})

    def text(v):
        return " ".join(paragraphs[int(p[1:])] for p in v["parrafos"])

    def proposal(v) -> str:
        """What the vote proposes, read from its last paragraphs (confirma / modifica / revoca …)."""
        tail = " ".join(paragraphs[int(p[1:])] for p in v["parrafos"][-3:])
        found = [(m.start(), name) for name, pat in RESULTADOS for m in re.finditer(pat, tail, re.IGNORECASE)]
        return max(found)[1] if found else ""

    resolutive_text = paragraphs[end] if end < len(paragraphs) else ""
    explicit = any(DISSENT.search(text(v)) for v in votes[1:])
    implicit = (len(votes) >= 2 and len(votes[1]["parrafos"]) >= 2
                and proposal(votes[0]) and proposal(votes[1]) and proposal(votes[0]) != proposal(votes[1]))
    dissent = bool(explicit or implicit)
    majority, minority = votes[0]["juez"], []
    if dissent:
        majority = ""
        for t in [text(v) for v in votes[2:] + votes[1:2]] + [resolutive_text]:
            m = JOINS.search(t)
            if m:
                surname = m.group(1).lower()
                majority = next((x["juez"] for x in votes if surname in x["juez"].lower()), "")
                if majority:
                    break
        minority = [v["juez"] for v in votes[:2] if majority and v["juez"] != majority]
    return {"votos": votes, "hay_disidencia": dissent, "voto_mayoria": majority, "votos_minoria": minority}
