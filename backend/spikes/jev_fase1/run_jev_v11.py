"""v1.1 run: fallo-level questions + paragraph function, with the vote structure computed in code.

3 runs with a fresh uid. Stores probabilities. Usage (from backend/): python -m spikes.jev_fase1.run_jev_v11
"""

import json
import sqlite3
import time
import uuid

from typesafe_sdk import TypeSafeClient

from scripts import quality
from scripts.config import settings
from scripts.labeling.state import build_state
from scripts.labeling.votes import detect_votes
from spikes.jev_fase1.questions import ES_V11, final_role, role_questions_v11
from spikes.jev_fase1.run_jev import OUT, SAMPLE, to_sdk

RUNS = 3


def main() -> None:
    ids = [x["id"] for x in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    with TypeSafeClient(api_key=settings.typesafe_api_key, model=settings.typesafe_model) as client:
        for k in range(RUNS):
            path = OUT / f"jev_v11_run{k}.jsonl"
            done = set()
            if path.exists():
                done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line}
            with path.open("a", encoding="utf-8") as f:
                for i in [i for i in ids if i not in done]:
                    doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
                    state = build_state(doc)
                    votes = detect_votes(quality.split_paragraphs(doc["texto"]))
                    questions = {**ES_V11, **role_questions_v11(state)}
                    t0 = time.perf_counter()
                    r = client.system_one({**state, "uid": uuid.uuid4().hex}, to_sdk(questions))
                    answers = {q: {"choice": a.choice, "confidence": a.confidence, "probabilities": a.probabilities}
                               for q, a in r.choices.items()}
                    for q, a in answers.items():
                        if q.startswith("rol_"):
                            a["final"] = final_role(a["choice"], q[4:], votes)
                    rec = {"id": i, "variant": "jev_v11", "model": r.model, "votes": votes,
                           "latency_s": round(time.perf_counter() - t0, 3),
                           "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                           "answers": answers}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"v1.1 run{k}: {len(ids) - len(done)} new -> {path.name}")


if __name__ == "__main__":
    main()
