"""v1.2: fallo-level questions over a state WITHOUT the dissenting vote (removed in code).

A dissent argues the opposite outcome; left in the state it pulls outcome questions the wrong
way. Roles keep the full state (v1.1). 3 runs. Usage: python -m spikes.jev_fase1.run_jev_v12
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
from spikes.jev_fase1.questions import ES_V11
from spikes.jev_fase1.run_jev import OUT, RELEVANT, SAMPLE, to_sdk

RUNS = int(__import__("os").environ.get("RUNS", "3"))


FILTERED = __import__("os").environ.get("FILTERED") == "1"   # also drop paragraphs unrelated to appeals/costs


def without_dissent(doc: dict) -> dict:
    paragraphs = quality.split_paragraphs(doc["texto"])
    votes = detect_votes(paragraphs)
    minority = {p for v in votes["votos"] if v["juez"] in votes["votos_minoria"] for p in v["parrafos"]}
    n = len(paragraphs)

    def keep(i: int, p: str) -> bool:
        if f"p{i}" in minority:
            return False
        return not FILTERED or i < 3 or i >= n - 6 or bool(RELEVANT.search(p))

    return build_state(doc, keep=keep)


def main() -> None:
    ids = [x["id"] for x in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    with TypeSafeClient(api_key=settings.typesafe_api_key, model=settings.typesafe_model) as client:
        for k in range(RUNS):
            path = OUT / f"jev_v12{'f' if FILTERED else ''}_run{k}.jsonl"
            done = set()
            if path.exists():
                done = {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line}
            with path.open("a", encoding="utf-8") as f:
                for i in [i for i in ids if i not in done]:
                    doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
                    state = without_dissent(doc)
                    t0 = time.perf_counter()
                    r = client.system_one({**state, "uid": uuid.uuid4().hex}, to_sdk(ES_V11))
                    rec = {"id": i, "variant": "jev_v12", "model": r.model,
                           "latency_s": round(time.perf_counter() - t0, 3),
                           "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                           "answers": {q: {"choice": a.choice, "confidence": a.confidence,
                                           "probabilities": a.probabilities} for q, a in r.choices.items()}}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"v1.2 run{k}: {len(ids) - len(done)} new -> {path.name}")


if __name__ == "__main__":
    main()
