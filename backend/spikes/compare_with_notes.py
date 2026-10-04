"""Compare our extracted fields with what a human-written note says about the same ruling.

The notes (news, bulletins, blogs) were written by people. Agents read ONLY the note and recorded its
claims (labels/bench/validacion_notas.jsonl); the citation (date, Sala, court) comes from the same note
(known_items.jsonl). Writes every disagreement to labels/bench/desacuerdos.jsonl, to be settled by reading
the ruling: the note can be wrong too (a publication date, a misread outcome).

Usage (from backend/): python -m spikes.compare_with_notes
"""

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date

from scripts.config import settings
from spikes.build_bench import OUT, fold
from spikes.quality_check import sala_key

PARTIAL_PAIRS = {"confirma", "revoca", "modifica", "hace lugar", "rechaza"}
NO_CLAIM = {"no lo dice", "otro", ""}


def dates_agree(cited: str, ours: str) -> bool:
    if len(cited) == 7:  # the note gave only the month
        return ours.startswith(cited)
    return abs((date.fromisoformat(cited[:10]) - date.fromisoformat(ours)).days) <= 7


def result_agrees(note: str, partial: bool, ours: str) -> str | None:
    if note in NO_CLAIM:
        return None
    if not ours:
        return "nos falta"
    if note == ours:
        return "coincide"
    # "confirmó y modificó los intereses", "admitió en parte": the first resolutive item can read either way
    if {note, ours} == {"confirma", "modifica"} or (partial and {note, ours} <= PARTIAL_PAIRS):
        return "zona gris"
    return "no coincide"


def norm_found(norm: dict, ours: list[str]) -> bool | None:
    if norm["cuerpo"] == "otra":
        return None
    if norm["cuerpo"] == "ley":
        digits = re.sub(r"\D", "", norm["ley"])
        if len(digits) < 4:
            return None
        return f"ley {int(digits):,}".replace(",", ".") in ours
    art = re.match(r"\d+", norm["articulo"] or "")
    if not art:
        return any(o.startswith(f"{norm['cuerpo']} art.") for o in ours)
    return f"{norm['cuerpo']} art. {art.group()}" in ours


def judge_signs(surname: str, firmantes: list[str]) -> bool:
    words = [w for w in fold(surname).split() if len(w) >= 3]
    return bool(words) and any(all(w in fold(f).split() for w in words) for f in firmantes)


def main() -> None:
    known = {r["doc_id"]: r for r in map(json.loads, open(OUT / "known_items.jsonl", encoding="utf-8"))}
    notes = [json.loads(line) for line in open(OUT / "validacion_notas.jsonl", encoding="utf-8")]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    tally: dict[str, Counter] = defaultdict(Counter)
    disagreements = []

    def record(field: str, verdict, doc: dict, note_says, ours, phrase: str = "") -> None:
        if verdict is None:
            return
        tally[field][verdict] += 1
        if verdict not in ("coincide",):
            disagreements.append({"doc_id": doc["id"], "fuero": known[doc["id"]]["fuero"], "campo": field,
                                  "veredicto": verdict, "la_nota_dice": note_says, "nosotros": ours, "frase": phrase,
                                  "fuente": known[doc["id"]]["fuentes"][0]["url"]})

    for n in notes:
        if n["doc_id"] not in known or not n["encontrado"]:
            tally["nota"]["no habla del fallo"] += 1
            continue
        tally["nota"]["habla del fallo"] += 1
        doc = db.execute("SELECT id, fecha, sala, instancia, resultado, normas, votos, firmantes, por_mayoria "
                         "FROM documents WHERE id=?", (n["doc_id"],)).fetchone()
        cita = known[n["doc_id"]]["cita"]
        if cita.get("fecha"):
            ok = dates_agree(cita["fecha"], doc["fecha"])
            record("fecha", "coincide" if ok else "no coincide", doc, cita["fecha"], doc["fecha"])
        if cita.get("sala") and doc["sala"]:
            ok = sala_key(re.sub(r"(?i)^sala\s+", "", cita["sala"])) == sala_key(doc["sala"])
            record("sala", "coincide" if ok else "no coincide", doc, cita["sala"], doc["sala"])
        instancia = "primera" if re.search(r"(?i)juzgado", cita.get("tribunal", "")) else "camara"
        record("instancia", "coincide" if instancia == doc["instancia"] else "no coincide", doc, instancia,
               doc["instancia"])
        record("resultado", result_agrees(n["resultado"], n["parcial"], doc["resultado"] or ""), doc,
               n["resultado"] + (" (parcial)" if n["parcial"] else ""), doc["resultado"], n["resultado_frase"])
        normas = json.loads(doc["normas"] or "[]")
        for norm in n["normas"]:
            hit = norm_found(norm, normas)
            label = (f"ley {norm['ley']}" if norm["cuerpo"] == "ley" else norm["cuerpo"]) + f" art. {norm['articulo']}"
            record("normas", None if hit is None else ("coincide" if hit else "no la tenemos"), doc, label, "")
        firmantes = json.loads(doc["firmantes"] or "[]")
        for juez in n["jueces"]:
            record("jueces", "coincide" if judge_signs(juez, firmantes) else "no firma", doc, juez, firmantes)
        votos = json.loads(doc["votos"] or "[]")
        if n["primer_voto"]:
            ok = bool(votos) and judge_signs(n["primer_voto"], [votos[0]])
            record("primer voto", "coincide" if ok else ("nos falta" if not votos else "no coincide"), doc,
                   n["primer_voto"], votos[:1])
        if n["mayoria"] != "no lo dice":
            ok = (n["mayoria"] == "mayoria") == bool(doc["por_mayoria"])
            record("mayoría", "coincide" if ok else "no coincide", doc, n["mayoria"], bool(doc["por_mayoria"]))

    for field, c in tally.items():
        total = sum(c.values())
        detail = " · ".join(f"{k} {v}" for k, v in c.most_common())
        share = f"{100 * c['coincide'] / total:.0f}% coincide" if field != "nota" else ""
        print(f"{field:<12} {total:>4}  {share:<14} {detail}")
    with open(OUT / "desacuerdos.jsonl", "w", encoding="utf-8") as f:
        for d in disagreements:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"\n{len(disagreements)} desacuerdos en {OUT / 'desacuerdos.jsonl'}")


if __name__ == "__main__":
    main()
