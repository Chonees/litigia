"""Same questions, same rulings, answered by Claude Haiku 4.5 with structured outputs.

Idempotent (cached per fallo). Usage (from backend/): python -m spikes.jev_fase1.run_haiku
"""

import json
import sqlite3
import time
from pathlib import Path

import anthropic

from scripts.config import settings
from scripts.labeling.state import build_state
from scripts.scrapers.pjn_tribunales import client_kwargs
from spikes.jev_fase1.questions import questions_for

MODEL = "claude-haiku-4-5"
PRICE_IN, PRICE_OUT = 1.0, 5.0     # USD per million tokens
SAMPLE = Path(__file__).parents[2] / "labels" / "gold" / "cnat_fase1_sample.json"
OUT = settings.data_root / "labels" / "fase1" / "haiku_es_full_run0.jsonl"

SYSTEM = (
    "Etiquetás sentencias de la Cámara Nacional de Apelaciones del Trabajo de Argentina. "
    "Para cada pregunta elegí exactamente una de las opciones, según su definición. "
    "Respondé solo con lo que dice la sentencia."
)


def render(questions: dict) -> str:
    lines = []
    for qid, q in questions.items():
        lines.append(f"## {qid}\n{q['instructions']}")
        for opt, desc in q["criteria"].items():
            lines.append(f"- {opt}" + (f": {desc}" if desc else ""))
    return "\n".join(lines)


def schema(questions: dict) -> dict:
    return {
        "type": "object",
        "properties": {qid: {"type": "string", "enum": list(q["criteria"])} for qid, q in questions.items()},
        "required": list(questions),
        "additionalProperties": False,
    }


def main() -> None:
    ids = [x["id"] for x in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    done = set()
    if OUT.exists():
        done = {json.loads(line)["id"] for line in OUT.read_text(encoding="utf-8").splitlines() if line}
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    client = anthropic.Anthropic(**client_kwargs(settings.anthropic_api_key, settings.anthropic_workspace_id))

    with OUT.open("a", encoding="utf-8") as f:
        for i in [i for i in ids if i not in done]:
            doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
            state = build_state(doc)
            questions = questions_for(state, "es")
            t0 = time.perf_counter()
            r = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM,
                messages=[{"role": "user", "content":
                           f"SENTENCIA (JSON):\n{json.dumps(state, ensure_ascii=False)}\n\nPREGUNTAS:\n{render(questions)}"}],
                output_config={"format": {"type": "json_schema", "schema": schema(questions)}},
            )
            latency = time.perf_counter() - t0
            text = next(b.text for b in r.content if b.type == "text")
            answers = json.loads(text)
            rec = {
                "id": i, "variant": "haiku_es_full", "model": r.model, "latency_s": round(latency, 3),
                "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                "cost_usd": (r.usage.input_tokens * PRICE_IN + r.usage.output_tokens * PRICE_OUT) / 1e6,
                "answers": {qid: {"choice": v, "confidence": 1.0} for qid, v in answers.items()},
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"haiku: {len(ids) - len(done)} new, {len(done)} cached -> {OUT.name}")


if __name__ == "__main__":
    main()
