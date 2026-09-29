"""Build the data for the human review page: Claude's gold vs. Jev's answers, with evidence paragraphs."""

import json
import sqlite3
import sys
from collections import Counter

from scripts import quality
from scripts.config import settings
from spikes.jev_fase1.evaluate import load_gold, load_run
from spikes.jev_fase1.evaluate_v11 import gold_v11
from spikes.jev_fase1.questions import V1_IDS

THRESHOLD = {q: 0.6 for q in V1_IDS} | {"materia_apelada": 0.5}
EVIDENCE_FROM_V0 = {"quien_apelo": "quien_apelo", "agravios_trabajador": "resultado_apelacion",
                    "agravios_demandada": "resultado_apelacion", "materia_apelada": "resultado_apelacion",
                    "costas_alzada": "costas_alzada"}


def consensus(runs, i, q):
    probs = Counter()
    for r in runs:
        for opt, p in r[i]["answers"][q]["probabilities"].items():
            probs[opt] += p / len(runs)
    opt, p = probs.most_common(1)[0]
    return {"label": opt if p >= THRESHOLD[q] else "sin_determinar", "top": opt, "prob": round(p, 2)}


def main(out_path: str) -> None:
    gold, gold0 = gold_v11(), load_gold()
    runs = [load_run(f"jev_v12_run{k}") for k in range(3)]
    roles = load_run("jev_v11_run0")
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    fallos = []
    for i in sorted(gold):
        doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
        paras = quality.split_paragraphs(doc["texto"])
        g, g0 = gold[i], gold0[i]
        preguntas = {}
        for q in V1_IDS:
            ev = g0.get("evidencia", {}).get(EVIDENCE_FROM_V0.get(q, ""), "")
            preguntas[q] = {"claude": g[q], "jev": consensus(runs, i, q),
                            "dudoso": q in g.get("dudoso", []) or (q in ("agravios_trabajador", "agravios_demandada")
                                                                   and "resultado_apelacion" in g0.get("dudoso", [])),
                            "evidencia": ev if ev and ev.startswith("p") else ""}
        jev_roles = {q[4:]: a["final"] for q, a in roles[i]["answers"].items() if q.startswith("rol_")}
        fallos.append({
            "id": i, "caratula": doc["caratula"], "tribunal": doc["tribunal"], "fecha": doc["fecha"],
            "expediente": doc["expediente"], "objeto": doc["objeto"], "url": doc["url"],
            "preguntas": preguntas,
            "holding_claude": [h for h in g0["holding"] if h != "ninguno"],
            "mayoria_jev": [p for p, r in jev_roles.items() if r == "razonamiento_mayoria"],
            "minoria_jev": [p for p, r in jev_roles.items() if r == "voto_minoria"],
            "votos": roles[i]["votes"],
            "notas_claude": " ".join(x for x in (g0.get("nota", ""), g.get("nota", "")) if x),
            "parrafos": paras,
        })
    json.dump(fallos, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    agree = sum(f["preguntas"][q]["claude"] == f["preguntas"][q]["jev"]["label"] for f in fallos for q in V1_IDS)
    print(f"{len(fallos)} fallos · {agree}/{len(fallos) * len(V1_IDS)} etiquetas coinciden")


if __name__ == "__main__":
    main(sys.argv[1])
