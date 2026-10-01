"""Accuracy of the stored enrichment against a blind gold extraction (labels/gold/enrich/batch*.jsonl).

Usage (from backend/): python -m spikes.evaluate_enrich [glob]      # default batch*.jsonl; holdout: holdout.jsonl
"""

import json
import sys
import re
import sqlite3
import unicodedata
from pathlib import Path

from scripts.config import settings
from spikes.quality_check import sala_key

GOLD = Path(__file__).parents[1] / "labels" / "gold" / "enrich"


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper().strip()


def surnames(names: list[str]) -> list[str]:
    out = []
    for n in names:
        words = [w for w in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", n) if len(w) > 2 and w.upper() not in ("DOCTOR", "DOCTORA")]
        if words:
            out.append(fold(words[-1]))
    return out


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def main() -> None:
    gold = {}
    pattern = sys.argv[1] if len(sys.argv) > 1 else "batch*.jsonl"
    for f in sorted(GOLD.glob(pattern)):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                g = json.loads(line)
                gold[g["id"]] = g
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    fields = {
        "instancia": lambda ours, g: ours["instancia"] == g["instancia"],
        "sala": lambda ours, g: sala_key(ours["sala"]) == sala_key(g["sala"]),        # "II" = "2"
        "resultado": lambda ours, g: ours["resultado"] == g["resultado"],
        "votos (mismos jueces, mismo orden)": lambda ours, g: surnames(json.loads(ours["votos"])) == surnames(g["votos"]),
        "numero de sentencia": lambda ours, g: digits(ours["numero"]) == digits(g["numero"]),
        # contencioso: rulings that only decide fees should be rejected as "solo_honorarios"
        "solo honorarios": lambda ours, g: ("solo_honorarios" in (ours["reasons"] or "")) == bool(g["solo_honorarios"]),
    }
    results = {k: [] for k in fields}
    for i, g in gold.items():
        ours = dict(db.execute("SELECT * FROM documents WHERE id=?", (i,)).fetchone())
        for name, ok in fields.items():
            if name == "sala" and (g["instancia"] != "camara" or not g["sala"]):   # the text does not name it
                continue
            if name == "solo honorarios" and "solo_honorarios" not in g:
                continue
            if name.startswith("votos") and g["instancia"] != "camara":
                continue
            results[name].append((ok(ours, g), i, ours, g))
    print(f"Gold ciego: {len(gold)} fallos\n")
    print(f"{'campo':38} {'exactitud':>10}   n")
    for name, rs in results.items():
        n = len(rs)
        print(f"{name:38} {sum(r[0] for r in rs) / max(1, n):10.1%}   {n}")
    print("\n-- errores (nuestro → gold)")
    for name, rs in results.items():
        for ok, i, ours, g in rs:
            if not ok:
                key = {"votos (mismos jueces, mismo orden)": "votos", "numero de sentencia": "numero"}.get(name, name)
                print(f"  {name:22} {i}: {ours[key]!s:40.40} → {g[key]!s:40.40} | {g.get('nota', '')[:70]}")


if __name__ == "__main__":
    main()
