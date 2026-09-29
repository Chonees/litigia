"""Run Jev over the Fase 1 sample. Idempotent: responses are cached per (variant, run, fallo).

Variants:
  es_full      Spanish questions, full ruling          (5 runs with a fresh uid: consistency)
  en_full      English questions, full ruling
  es_filtered  Spanish questions, only header + appeal/costs paragraphs + last paragraphs

Usage (from backend/): python -m spikes.jev_fase1.run_jev [--runs 5]
"""

import argparse
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

from typesafe_sdk import Choice, TypeSafeClient

from scripts import quality
from scripts.config import settings
from scripts.labeling.state import build_state
from spikes.jev_fase1.questions import questions_for

SAMPLE = Path(__file__).parents[2] / "labels" / "gold" / "cnat_fase1_sample.json"
OUT = settings.data_root / "labels" / "fase1"
RELEVANT = re.compile(r"agravi|apel|recurr|se\s+alza|queja|costas|resuelve|confirm|revoc|modific", re.IGNORECASE)


def filtered(state_doc: dict) -> dict:
    n = len(quality.split_paragraphs(state_doc["texto"]))
    return build_state(state_doc, keep=lambda i, p: i < 3 or i >= n - 6 or bool(RELEVANT.search(p)))


VARIANTS = {
    "es_full": ("es", build_state),
    "en_full": ("en", build_state),
    "es_filtered": ("es", filtered),
}


def to_sdk(questions: dict) -> dict:
    return {qid: Choice(instructions=q["instructions"], criteria=q["criteria"]) for qid, q in questions.items()}


def run_one(client: TypeSafeClient, doc: dict, variant: str, uid: str | None) -> dict:
    lang, make_state = VARIANTS[variant]
    state = make_state(doc)
    questions = questions_for(state, lang)
    if variant == "es_filtered":
        questions.pop("holding")          # options would only cover the kept paragraphs
    if uid:
        state = {**state, "uid": uid}
    t0 = time.perf_counter()
    r = client.system_one(state, to_sdk(questions))
    latency = time.perf_counter() - t0
    return {
        "id": doc["id"], "variant": variant, "model": r.model, "latency_s": round(latency, 3),
        "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
        "answers": {
            qid: {"choice": a.choice, "confidence": a.confidence, "probabilities": a.probabilities}
            for qid, a in r.choices.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5, help="Repeats of es_full for consistency")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    ids = [x["id"] for x in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    docs = {i: dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone()) for i in ids}

    plan = [("es_full", k) for k in range(args.runs)] + [("en_full", 0), ("es_filtered", 0)]
    with TypeSafeClient(api_key=settings.typesafe_api_key, model=settings.typesafe_model) as client:
        for variant, k in plan:
            path = OUT / f"jev_{variant}_run{k}.jsonl"
            done = set()
            if path.exists():
                done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line}
            todo = [i for i in ids if i not in done]
            with path.open("a", encoding="utf-8") as f:
                for i in todo:
                    uid = uuid.uuid4().hex if variant == "es_full" and args.runs > 1 else None
                    rec = run_one(client, docs[i], variant, uid)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{variant} run{k}: {len(todo)} new, {len(done)} cached -> {path.name}")


if __name__ == "__main__":
    main()
