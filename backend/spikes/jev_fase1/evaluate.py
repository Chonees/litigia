"""Evaluate the Fase 1 runs against the gold set. Usage (from backend/): python -m spikes.jev_fase1.evaluate"""

import json
from collections import defaultdict
from pathlib import Path

from scripts.config import settings
from scripts.labeling.metrics import Answer, at_threshold, calibration, consistency, is_correct
from spikes.jev_fase1.questions import QUESTION_IDS

GOLD_DIR = Path(__file__).parents[2] / "labels" / "gold"
RUNS = settings.data_root / "labels" / "fase1"
JEV_PRICE = 0.042      # USD per million input tokens (jev-1.13.0, docs 2026-09)
THRESHOLDS = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)
PROJECTED_FALLOS = 60_000


def load_gold() -> dict:
    gold = {}
    for part in sorted((GOLD_DIR / "parts").glob("batch[0-9].jsonl")):
        for line in part.read_text(encoding="utf-8").splitlines():
            if line.strip():
                g = json.loads(line)
                gold[g["id"]] = g
    merged = GOLD_DIR / "cnat_fase1_gold_v0.jsonl"
    merged.write_text("\n".join(json.dumps(gold[i], ensure_ascii=False) for i in sorted(gold)) + "\n", encoding="utf-8")
    return gold


def load_run(name: str) -> dict:
    path = RUNS / f"{name}.jsonl"
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())} if path.exists() else {}


def gold_value(g: dict, qid: str):
    return set(g["holding"]) if qid == "holding" else g[qid]


def answers(run: dict, gold: dict, qid: str, skip_doubtful: bool = False) -> list[Answer]:
    out = []
    for i, r in run.items():
        if qid not in r["answers"] or i not in gold:
            continue
        if skip_doubtful and qid in gold[i].get("dudoso", []):
            continue
        a = r["answers"][qid]
        out.append(Answer(i, a["choice"], a["confidence"], gold_value(gold[i], qid)))
    return out


def pct(x) -> str:
    return "—" if x is None else f"{100 * x:.0f}%"


def main() -> None:
    gold = load_gold()
    print(f"Gold: {len(gold)} fallos · dudosos por pregunta:",
          {q: sum(q in g.get("dudoso", []) for g in gold.values()) for q in QUESTION_IDS})

    variants = {
        "jev es_full": load_run("jev_es_full_run0"),
        "jev en_full": load_run("jev_en_full_run0"),
        "jev es_filtered": load_run("jev_es_filtered_run0"),
        "haiku es_full": load_run("haiku_es_full_run0"),
    }

    print("\n== 1.6 Precisión sin umbral (todos / sin dudosos)")
    print(f"{'pregunta':22}" + "".join(f"{v:>22}" for v in variants))
    for q in QUESTION_IDS:
        row = f"{q:22}"
        for run in variants.values():
            a_all, a_clean = answers(run, gold, q), answers(run, gold, q, skip_doubtful=True)
            if not a_all:
                row += f"{'—':>22}"
                continue
            acc = lambda xs: sum(is_correct(x.predicted, x.gold) for x in xs) / len(xs)
            row += f"{pct(acc(a_all)) + ' / ' + pct(acc(a_clean)):>22}"
        print(row)

    print("\n== Cobertura y precisión por umbral de confianza (jev es_full, todos los fallos)")
    print(f"{'pregunta':22}" + "".join(f"{'≥' + str(t):>14}" for t in THRESHOLDS))
    for q in QUESTION_IDS:
        a = answers(variants["jev es_full"], gold, q)
        cells = [at_threshold(a, t) for t in THRESHOLDS]
        print(f"{q:22}" + "".join(f"{pct(c['accuracy']) + ' @' + pct(c['coverage']):>14}" for c in cells))

    print("\n== 1.7 Calibración (jev es_full, todas las preguntas juntas)")
    pooled = [x for q in QUESTION_IDS for x in answers(variants["jev es_full"], gold, q)]
    for b in calibration(pooled):
        print(f"  confianza {b['bin']}: n={b['n']:3}  confianza media {b['mean_confidence']:.2f}  acierto {b['accuracy']:.2f}")

    print("\n== 1.8 Consistencia (5 corridas de jev es_full con uid distinto)")
    runs = [load_run(f"jev_es_full_run{k}") for k in range(5)]
    runs = [r for r in runs if r]
    for q in QUESTION_IDS:
        per_run = [{i: (r["answers"][q]["choice"], r["answers"][q]["confidence"]) for i, r in run.items()} for run in runs]
        cells = "  ".join(f"≥{t}: {pct(consistency(per_run, t if t else None))}" for t in (0.0, 0.6, 0.8))
        print(f"  {q:22} {cells}")

    print("\n== 1.11 Costo y latencia")
    for name, run in variants.items():
        if not run:
            continue
        toks = [r["input_tokens"] for r in run.values()]
        lat = sorted(r["latency_s"] for r in run.values())
        cost = sum(r.get("cost_usd", r["input_tokens"] * JEV_PRICE / 1e6) for r in run.values()) / len(run)
        print(f"  {name:16} tokens/fallo {sum(toks) / len(toks):7.0f} · latencia p50 {lat[len(lat) // 2]:.2f}s p90 "
              f"{lat[int(len(lat) * .9)]:.2f}s · ${cost:.6f}/fallo · proyectado {PROJECTED_FALLOS:,} fallos: ${cost * PROJECTED_FALLOS:,.2f}")
    models = {r["model"] for r in variants["jev es_full"].values()}
    print("  modelo que respondió:", models)

    print("\n== 1.12 Errores de jev es_full (para análisis)")
    for q in QUESTION_IDS:
        for x in answers(variants["jev es_full"], gold, q):
            if not is_correct(x.predicted, x.gold):
                doubt = "DUDOSO " if q in gold[x.item].get("dudoso", []) else ""
                print(f"  {doubt}{x.item} {q}: jev={x.predicted} ({x.confidence:.2f}) gold={x.gold}")


if __name__ == "__main__":
    main()
