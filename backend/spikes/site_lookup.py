"""Why is a ruling cited by a third party missing from our catalog? Ask the PJN site for it by carátula.

For each ruling in labels/bench/cobertura.jsonl that we do not have, search the site by a party word of the
carátula around the cited date, first among sentencias definitivas (what we collect) and then among
interlocutorias. Prints what the site lists, so each gap can be told apart: not a definitiva, not published,
or missed by us. One search at a time, spaced like the scraper.

Usage (from backend/): python -m spikes.site_lookup
"""

import calendar
import json
import re
import sqlite3
from collections import Counter
from datetime import date, timedelta

from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CaptchaSolver, PJNSite
from spikes.build_bench import GENERIC, OUT, fold, party_words

FUERO_CAMARA = {"laboral": "C_7", "seguridad social": "C_5", "contencioso": "C_2", "civil": "C_1", "comercial": "C_10"}
MARGIN = timedelta(days=30)
SKIP = {"INCIDENTE", "ACTOR", "DEMANDADO"}


def window(fecha: str) -> tuple[date, date]:
    if len(fecha) == 7:  # the source gave only the month
        y, m = map(int, fecha.split("-"))
        return date(y, m, 1) - MARGIN, date(y, m, calendar.monthrange(y, m)[1]) + MARGIN
    d = date.fromisoformat(fecha[:10])
    return d - MARGIN, d + MARGIN


def search_word(caratula: str, df: Counter) -> str:
    """The rarest word of the first party (the site caps a search at 100 results), else of any party."""
    first = fold(caratula).split(" C/")[0]
    words = (party_words(first) or party_words(caratula)) - GENERIC - SKIP
    return min(sorted(words), key=lambda w: df[w]) if words else ""


def _sides(caratula: str) -> list[set[str]]:
    """Distinctive words of each side of "actor c/ demandado"; one set when there is no "c/"."""
    parties = re.split(r"\s+S\s*/", fold(caratula))[0]
    return [set(re.findall(r"[A-Z]{4,}", side)) - GENERIC - SKIP for side in re.split(r"\bC\s*/", parties, maxsplit=1)]


def is_same_case(cited: str, listed: str) -> bool:
    """Both sides share a word; with one side (or a generic one, like ANSES), two words in common.

    One shared word matches strangers: the same bank suing other debtors, a namesake suing another ART.
    """
    c, l = _sides(cited), _sides(listed)
    if len(c) == len(l) == 2 and all(c):
        return bool(c[0] & l[0]) and bool(c[1] & l[1])
    words = set().union(*c)
    return len(words & set().union(*l)) >= min(2, len(words)) > 0


def main() -> None:
    missing = [json.loads(line) for line in open(OUT / "cobertura.jsonl", encoding="utf-8")]
    missing = [r for r in missing if r["status"] != "found"]
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    df = Counter(w for (car,) in db.execute("SELECT caratula FROM documents WHERE active=1") for w in party_words(car))
    site = PJNSite(CaptchaSolver())
    for r in missing:
        cita, camara = r["cita"], FUERO_CAMARA[r["fuero"]]
        word = search_word(cita["caratula"], df)
        print(f"\n== {r['fuero']} · {cita.get('sala') or '-'} · {cita['fecha']} · {cita['caratula'][:80]}", flush=True)
        if not word:
            print("   sin una palabra de la carátula para buscar (iniciales)", flush=True)
            continue
        start, end = window(cita["fecha"])
        for tipo in ("D", "I"):
            total, results = site.search("5-5", camara, "", tipo, start, end, caratula=word)
            hits = [x for x in results if is_same_case(cita["caratula"], x["caratula"])]
            print(f"   {tipo} '{word}' {start}..{end}: el sitio lista {total}, el caso citado {len(hits)}", flush=True)
            for x in hits[:5]:
                print(f"      {x['fecha']} · {x['tribunal']} · {x['caratula'][:70]} · {x['expediente']}", flush=True)
            if hits:
                break
    print(f"\ncaptcha ${site.solver.cost:.4f} · búsquedas {site.searches}", flush=True)


if __name__ == "__main__":
    main()
