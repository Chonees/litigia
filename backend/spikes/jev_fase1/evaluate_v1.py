"""Evaluate the v1 run (per-party outcomes + paragraph roles). Usage: python -m spikes.jev_fase1.evaluate_v1"""

import json
from collections import Counter

from scripts.labeling.metrics import Answer, at_threshold, calibration, consistency, is_correct
from spikes.jev_fase1.evaluate import GOLD_DIR, JEV_PRICE, PROJECTED_FALLOS, load_gold, load_run, pct
from spikes.jev_fase1.questions import V1_IDS

THRESHOLDS = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9)
KEY_ROLES = ("agravio", "razonamiento_mayoria", "voto_minoria", "resolutivo")


def load_gold_v1() -> dict:
    gold = {}
    for part in sorted((GOLD_DIR / "parts").glob("batch*_v1.jsonl")):
        for line in part.read_text(encoding="utf-8").splitlines():
            if line.strip():
                g = json.loads(line)
                gold[g["id"]] = g
    # tipo_caso and costas_alzada did not change from v0: take them from the v0 gold when missing.
    for i, g0 in load_gold().items():
        if i in gold:
            for q in ("tipo_caso", "costas_alzada"):
                gold[i].setdefault(q, g0[q])
                if q in g0.get("dudoso", []) and q not in gold[i].setdefault("dudoso", []):
                    gold[i]["dudoso"].append(q)
    (GOLD_DIR / "cnat_fase1_gold_v1.jsonl").write_text(
        "\n".join(json.dumps(gold[i], ensure_ascii=False) for i in sorted(gold)) + "\n", encoding="utf-8")
    return gold


def answers(run: dict, gold: dict, qid: str, skip_doubtful=False) -> list[Answer]:
    out = []
    for i, r in run.items():
        if i in gold and qid in r["answers"] and not (skip_doubtful and qid in gold[i].get("dudoso", [])):
            a = r["answers"][qid]
            out.append(Answer(i, a["choice"], a["confidence"], gold[i][qid]))
    return out


def role_answers(run: dict, gold: dict) -> list[Answer]:
    out = []
    for i, r in run.items():
        for pid, role in gold.get(i, {}).get("roles", {}).items():
            a = r["answers"].get(f"rol_{pid}")
            if a:
                out.append(Answer(f"{i}:{pid}", a["choice"], a["confidence"], role))
    return out


def main() -> None:
    gold = load_gold_v1()
    gold_v0 = load_gold()
    runs = [r for r in (load_run(f"jev_v1_run{k}") for k in range(3)) if r]
    run0 = runs[0]
    print(f"Gold v1: {len(gold)} fallos · dudosos:",
          {q: sum(q in g.get("dudoso", []) for g in gold.values()) for q in V1_IDS},
          "· roles dudosos:", sum(sum(d.startswith("roles:") for d in g.get("dudoso", [])) for g in gold.values()))

    print("\n== Preguntas por fallo: acierto @ cobertura por umbral · consistencia (3 corridas)")
    print(f"{'pregunta':22}" + "".join(f"{'≥' + str(t):>13}" for t in THRESHOLDS) + "   consistencia ≥0.6 / ≥0.8")
    for q in V1_IDS:
        a = answers(run0, gold, q)
        cells = [at_threshold(a, t) for t in THRESHOLDS]
        per = [{i: (r["answers"][q]["choice"], r["answers"][q]["confidence"]) for i, r in run.items()} for run in runs]
        print(f"{q:22}" + "".join(f"{pct(c['accuracy']) + '@' + pct(c['coverage']):>13}" for c in cells)
              + f"   {pct(consistency(per, 0.6))} / {pct(consistency(per, 0.8))}")

    print("\n== Rol de cada párrafo")
    ra = role_answers(run0, gold)
    for t in (0.0, 0.6, 0.8, 0.9):
        c = at_threshold(ra, t)
        print(f"  ≥{t}: acierto {pct(c['accuracy'])} sobre {pct(c['coverage'])} de {c['n']} párrafos")
    confusion = Counter((x.gold, x.predicted) for x in ra if x.gold != x.predicted)
    print("  confusiones más frecuentes (gold → jev):", confusion.most_common(8))
    for role in KEY_ROLES:
        g = [x for x in ra if x.gold == role]
        p = [x for x in ra if x.predicted == role]
        if g:
            print(f"  {role:22} recall {pct(sum(x.predicted == role for x in g) / len(g))} (n={len(g)}) · "
                  f"precision {pct(sum(x.gold == role for x in p) / len(p)) if p else '—'}")
    per_roles = [{x.item: (x.predicted, x.confidence) for x in role_answers(run, gold)} for run in runs]
    print(f"  consistencia de roles: ≥0.6 {pct(consistency(per_roles, 0.6))} · ≥0.8 {pct(consistency(per_roles, 0.8))}")

    print("\n== El holding sale de los roles: ¿los párrafos del holding (gold v0) quedan como razonamiento_mayoria?")
    hit = tot = 0
    for i, g in gold_v0.items():
        hs = [h for h in g["holding"] if h != "ninguno"]
        if not hs or i not in run0:
            continue
        tot += 1
        roles = {q[4:]: a["choice"] for q, a in run0[i]["answers"].items() if q.startswith("rol_")}
        hit += any(roles.get(h) == "razonamiento_mayoria" for h in hs)
    print(f"  fallos con al menos un párrafo del holding marcado razonamiento_mayoria: {hit}/{tot} ({pct(hit / tot)})")

    print("\n== Trampas de voto en disidencia (primer voto en minoría)")
    for i in ("488c04a40db12501", "ee0bc6f17471be9f"):
        g = gold[i]["roles"]
        minority = [p for p, r in g.items() if r == "voto_minoria"]
        roles = {q[4:]: a["choice"] for q, a in run0[i]["answers"].items() if q.startswith("rol_")}
        got = [p for p in minority if roles.get(p) == "voto_minoria"]
        wrong = [p for p in minority if roles.get(p) == "razonamiento_mayoria"]
        print(f"  {i}: {len(minority)} párrafos de minoría · jev los marca minoría: {len(got)} · como mayoría: {len(wrong)}")

    print("\n== Calibración (preguntas por fallo + roles)")
    pooled = [x for q in V1_IDS for x in answers(run0, gold, q)] + ra
    for b in calibration(pooled):
        print(f"  {b['bin']}: n={b['n']:4}  confianza media {b['mean_confidence']:.2f}  acierto {b['accuracy']:.2f}")

    toks = [r["input_tokens"] for r in run0.values()]
    lat = sorted(r["latency_s"] for r in run0.values())
    cost = sum(toks) / len(toks) * JEV_PRICE / 1e6
    print(f"\n== Costo: {sum(toks) / len(toks):.0f} tokens/fallo · latencia p50 {lat[len(lat) // 2]:.2f}s · "
          f"${cost:.6f}/fallo · {PROJECTED_FALLOS:,} fallos: ${cost * PROJECTED_FALLOS:,.2f} · modelo {set(r['model'] for r in run0.values())}")

    print("\n== Errores (preguntas por fallo, corrida 0)")
    for q in V1_IDS:
        for x in answers(run0, gold, q):
            if not is_correct(x.predicted, x.gold):
                d = "DUDOSO " if q in gold[x.item].get("dudoso", []) else ""
                print(f"  {d}{x.item} {q}: jev={x.predicted} ({x.confidence:.2f}) gold={x.gold}")


if __name__ == "__main__":
    main()
