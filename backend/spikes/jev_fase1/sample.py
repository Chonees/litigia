"""Pick the Fase 1 mini gold set: 30 CNAT rulings stratified by objeto, fixed seed."""

import json
import random
import sqlite3
from pathlib import Path

from scripts import quality
from scripts.config import settings

OUT = Path(__file__).parents[2] / "labels" / "gold" / "cnat_fase1_sample.json"
STRATA = [("DESPIDO", 10), ("ACCIDENTE - LEY ESPECIAL", 10), ("RECURSO LEY 27348", 7), (None, 3)]
MAX_CHARS = 60_000      # the 3 giants are handled in production by filtering paragraphs
MAX_PARAGRAPHS = 250    # a Choice accepts up to 255 options


def main() -> None:
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    rows = db.execute(
        "SELECT id, objeto, texto FROM documents WHERE active=1 AND status='indexable' "
        "AND tribunal LIKE '%TRABAJO%' AND chars <= ? ORDER BY id", (MAX_CHARS,)
    ).fetchall()
    rows = [(i, o) for i, o, t in rows if len(quality.split_paragraphs(t)) <= MAX_PARAGRAPHS]
    main_objetos = {o for o, _ in STRATA if o}
    rng = random.Random(20260927)
    picked = []
    for objeto, n in STRATA:
        pool = [i for i, o in rows if (o == objeto if objeto else o not in main_objetos)]
        picked += [{"id": i, "estrato": objeto or "OTROS"} for i in rng.sample(pool, n)]
    OUT.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(picked)} fallos -> {OUT}")


if __name__ == "__main__":
    main()
