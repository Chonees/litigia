"""Evaluate v1.1 (party outcomes with 4 options; paragraph roles with majority/dissent from code).

Usage (from backend/): python -m spikes.jev_fase1.evaluate_v11
"""

from collections import Counter

from scripts.labeling.metrics import Answer, at_threshold, calibration, consistency, is_correct
from spikes.jev_fase1.evaluate import JEV_PRICE, PROJECTED_FALLOS, load_gold, load_run, pct
from spikes.jev_fase1.evaluate_v1 import load_gold_v1
from spikes.jev_fase1.questions import V1_IDS

THRESHOLDS = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)
# Gold v1 → v1.1 options. Overrides follow the labelers' own notes: the appeal was declared
# desierta but one grievance was still decided on the merits (and rejected).
MERGE = {"admitidos_en_parte": "admitidos"}
OVERRIDES = {("456b1294e39eb506", "agravios_demandada"): "rechazados",
             ("181a667d898c9351", "agravios_trabajador"): "rechazados"}
NOT_FORMAL_DISSENT = {"4c44ad484d87fd97", "625e1d5284dc07a8"}   # argue, then join the majority


def gold_v11() -> dict:
    gold = load_gold_v1()
    for i, g in gold.items():
        for q in ("agravios_trabajador", "agravios_demandada"):
            g[q] = OVERRIDES.get((i, q), MERGE.get(g[q], g[q]))
    return gold


def answers(run, gold, q):
    return [Answer(i, r["answers"][q]["choice"], r["answers"][q]["confidence"], gold[i][q])
            for i, r in run.items() if i in gold and q in r["answers"]]


def role_answers(run, gold, skip=frozenset()):
    return [Answer(f"{i}:{pid}", r["answers"][f"rol_{pid}"]["final"], r["answers"][f"rol_{pid}"]["confidence"], role)
            for i, r in run.items() if i not in skip
            for pid, role in gold.get(i, {}).get("roles", {}).items() if f"rol_{pid}" in r["answers"]]


def main() -> None:
    gold = gold_v11()
    runs = [r for r in (load_run(f"jev_v11_run{k}") for k in range(3)) if r]
    run0 = runs[0]

    print("== Preguntas por fallo: acierto@cobertura por umbral · consistencia 3 corridas (≥0.6 / ≥0.8)")
    print(f"{'pregunta':22}" + "".join(f"{'≥' + str(t):>13}" for t in THRESHOLDS))
    for q in V1_IDS:
        a = answers(run0, gold, q)
        per = [{i: (r["answers"][q]["choice"], r["answers"][q]["confidence"]) for i, r in run.items()} for run in runs]
        print(f"{q:22}" + "".join(f"{pct(c['accuracy']) + '@' + pct(c['coverage']):>13}"
                                   for c in (at_threshold(a, t) for t in THRESHOLDS))
              + f"   {pct(consistency(per, 0.6))} / {pct(consistency(per, 0.8))}")

    print("\n== Rol de cada párrafo (mayoría/minoría asignadas por código)")
    for label, skip in (("todos", frozenset()), ("sin los 2 casos que no son disidencia formal", NOT_FORMAL_DISSENT)):
        ra = role_answers(run0, gold, skip)
        print(f"  [{label}] " + " · ".join(
            f"≥{c['threshold']}: {pct(c['accuracy'])}@{pct(c['coverage'])}" for c in (at_threshold(ra, t) for t in (0.0, 0.6, 0.8))))
    ra = role_answers(run0, gold, NOT_FORMAL_DISSENT)
    for role in ("agravio", "razonamiento_mayoria", "voto_minoria", "resolutivo"):
        g = [x for x in ra if x.gold == role]
        p = [x for x in ra if x.predicted == role]
        print(f"  {role:22} recall {pct(sum(x.predicted == role for x in g) / len(g))} (n={len(g)}) · "
              f"precision {pct(sum(x.gold == role for x in p) / len(p)) if p else '—'}")
    print("  confusiones (gold → final):", Counter((x.gold, x.predicted) for x in ra if x.gold != x.predicted).most_common(6))
    per_roles = [{x.item: (x.predicted, x.confidence) for x in role_answers(run, gold)} for run in runs]
    print(f"  consistencia de roles: ≥0.6 {pct(consistency(per_roles, 0.6))} · ≥0.8 {pct(consistency(per_roles, 0.8))}")

    print("\n== Trampas de disidencia (párrafos de minoría gold → marcados minoría)")
    for i in ("488c04a40db12501", "ee0bc6f17471be9f", "01ceaa06345f9b17"):
        gm = [p for p, r in gold[i]["roles"].items() if r == "voto_minoria"]
        ok = sum(run0[i]["answers"][f"rol_{p}"]["final"] == "voto_minoria" for p in gm)
        print(f"  {i}: {ok}/{len(gm)}")

    print("\n== Holding: ¿algún párrafo del holding (gold v0) queda como razonamiento_mayoria?")
    v0 = load_gold()
    hits = [(i, any(run0[i]["answers"].get(f"rol_{h}", {}).get("final") == "razonamiento_mayoria" for h in g["holding"]))
            for i, g in v0.items() if i in run0 and g["holding"] != ["ninguno"]]
    print(f"  {sum(h for _, h in hits)}/{len(hits)}")

    print("\n== Calibración (todo junto)")
    pooled = [x for q in V1_IDS for x in answers(run0, gold, q)] + role_answers(run0, gold, NOT_FORMAL_DISSENT)
    for b in calibration(pooled):
        print(f"  {b['bin']}: n={b['n']:4} confianza media {b['mean_confidence']:.2f} acierto {b['accuracy']:.2f}")

    toks = [r["input_tokens"] for r in run0.values()]
    cost = sum(toks) / len(toks) * JEV_PRICE / 1e6
    lat = sorted(r["latency_s"] for r in run0.values())
    print(f"\n== Costo: {sum(toks) / len(toks):.0f} tokens/fallo · p50 {lat[len(lat) // 2]:.2f}s · "
          f"{PROJECTED_FALLOS:,} fallos ${cost * PROJECTED_FALLOS:,.2f} · {set(r['model'] for r in run0.values())}")

    print("\n== Errores de preguntas por fallo")
    for q in V1_IDS:
        for x in answers(run0, gold, q):
            if not is_correct(x.predicted, x.gold):
                print(f"  {'DUDOSO ' if q in gold[x.item].get('dudoso', []) else ''}{x.item} {q}: "
                      f"jev={x.predicted} ({x.confidence:.2f}) gold={x.gold}")


if __name__ == "__main__":
    main()
