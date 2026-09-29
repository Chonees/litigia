"""Run Jev with the v1 questions: 6 fallo-level questions + one role question per paragraph, one request per fallo.

3 runs with a fresh uid (consistency). Idempotent. Usage (from backend/): python -m spikes.jev_fase1.run_jev_v1
"""

import json
import sqlite3
import time
import uuid

from typesafe_sdk import Choice, TypeSafeClient

from scripts.config import settings
from scripts.labeling.state import build_state
from spikes.jev_fase1.questions import ES_V1, role_questions
from spikes.jev_fase1.run_jev import OUT, SAMPLE, to_sdk

RUNS = 3


def main() -> None:
    ids = [x["id"] for x in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    with TypeSafeClient(api_key=settings.typesafe_api_key, model=settings.typesafe_model) as client:
        for k in range(RUNS):
            path = OUT / f"jev_v1_run{k}.jsonl"
            done = set()
            if path.exists():
                done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line}
            with path.open("a", encoding="utf-8") as f:
                for i in [i for i in ids if i not in done]:
                    doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
                    state = build_state(doc)
                    questions = {**ES_V1, **role_questions(state)}
                    t0 = time.perf_counter()
                    r = client.system_one({**state, "uid": uuid.uuid4().hex}, to_sdk(questions))
                    rec = {
                        "id": i, "variant": "jev_v1", "model": r.model,
                        "latency_s": round(time.perf_counter() - t0, 3),
                        "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                        "answers": {q: {"choice": a.choice, "confidence": a.confidence} for q, a in r.choices.items()},
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"v1 run{k}: {len(ids) - len(done)} new -> {path.name}")


if __name__ == "__main__":
    main()
