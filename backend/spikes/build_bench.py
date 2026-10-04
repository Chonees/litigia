"""Build the search benchmark from the output of the multi-agent workflow (public sources, no access to our DB).

Two sets, frozen once written:
- known_items.jsonl: rulings that a third party (news, bulletin, blog) described and cited. The query paraphrases
  the source's description; the right answer is the ruling the source cites, located in our catalog.
- queries.jsonl: litigator queries built from doctrine, with a relevance rule written before any search.
And cobertura.jsonl: every in-scope ruling the sources cited, and whether our catalog has it.

Applies the critics' verdicts, re-checks leaks with code (party names, case numbers, copied spans), drops
duplicates and assigns a stable dev/test split by content hash.

Usage (from backend/): python -m spikes.build_bench <round1_result.json> [<round2_result.json> ...]
"""

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from scripts.config import settings

OUT = Path(__file__).resolve().parents[1] / "labels" / "bench"
DEV_SHARE = 3  # out of 10; the rest is the frozen test set
COPIED_SPAN = 8  # consecutive words shared with the source = the query copies it
COMMON_DF = 20  # a word in this many carátulas does not point to one ruling
CASE_NUMBER = re.compile(r"\b\d{1,6}\s*/\s*(?:19|20)\d{2}\b")
NORM_BEFORE = re.compile(r"\b(?:LEY|LEYES|DECRETO|DTO|DNU|RES|RESOLUCION|RESOLUCIONES|SSN|ACORDADA|ACTA|"
                         r"DISPOSICION|COMUNICACION|CIRCULAR)\b")

# words of a carátula that name a whole class of litigants (thousands of cases), not one party
GENERIC = set("""
ESTADO NACIONAL NACION ARGENTINA ARGENTINO ANSES ADMINISTRACION FEDERAL INGRESOS PUBLICOS AFIP ARCA DIRECCION
GENERAL IMPOSITIVA ADUANAS ADUANA MINISTERIO GOBIERNO CIUDAD AUTONOMA BUENOS AIRES PODER EJECUTIVO BANCO SEGUROS
SEGURO ASEGURADORA COMPANIA SOCIEDAD ANONIMA OTRO OTROS OTRA OTRAS POLICIA FUERZA AEREA EJERCITO ARMADA GENDARMERIA
PREFECTURA NAVAL MIGRACIONES CONSORCIO PROPIETARIOS CAJA RETIROS JUBILACIONES PENSIONES SERVICIO PENITENCIARIO
SUPERINTENDENCIA RIESGOS TRABAJO ENTE REGULADOR COMISION NACIONALES VALORES MEDICA CENTRAL SUCESION
""".split())


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def _words(s: str) -> list[str]:
    return re.findall(r"[A-Z0-9]+", fold(s))


def party_words(caratula: str) -> set[str]:
    """Words of the parties: the carátula before "s/" (the object of the case comes after)."""
    return set(re.findall(r"[A-Z]{4,}", re.split(r"\s+S\s*/", fold(caratula))[0]))


def leaked_words(query: str, caratula: str, common: set[str] = frozenset()) -> set[str]:
    """Party names of the carátula that the query repeats, except words shared by many carátulas."""
    return (party_words(caratula) - GENERIC - common) & set(_words(query))


def copies(query: str, source: str, n: int = COPIED_SPAN) -> bool:
    q, s = _words(query), " ".join(_words(source))
    return any(" ".join(q[i:i + n]) in s for i in range(len(q) - n + 1))


def leaks(query: str, cita: dict, excerpt: str, common: set[str] = frozenset()) -> list[str]:
    reasons = ["nombra a una parte"] if leaked_words(query, cita.get("caratula", ""), common) else []
    # "DNU 274/2024" or "resoluciones SSN 1039/2019 y 332/2023" cite norms, not the case
    if any(not NORM_BEFORE.search(fold(query[max(0, m.start() - 30):m.start()]))
           for m in CASE_NUMBER.finditer(query)):
        reasons.append("número de expediente")
    if copies(query, excerpt):
        reasons.append("copia la fuente")
    return reasons


def split(key: str) -> str:
    return "dev" if int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % 10 < DEV_SHARE else "test"


def _id(prefix: str, *parts: str) -> str:
    return prefix + hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def build(data: dict, common: set[str] = frozenset()) -> tuple[list[dict], list[dict], list[dict], Counter]:
    reviews = {r["key"]: r for r in data.get("reviews", [])}
    dropped: Counter = Counter()
    known: dict[str, dict] = {}
    coverage: dict[str, dict] = {}
    for it in data["known"]:
        m, cita = it["match"], it["cita"]
        cov_key = m["doc_id"] or fold(cita.get("caratula", ""))[:40] + "|" + cita.get("fecha", "")
        if m["status"] != "out_of_scope":
            row = coverage.setdefault(cov_key, {"fuero": it["fuero"], "tipo_caso": it["tipo_caso"], "cita": cita,
                                                "status": m["status"], "doc_id": m["doc_id"], "fuentes": []})
            row["fuentes"].append(it["source_url"])
        if m["status"] != "found":
            dropped[f"conocido: {m['status']}"] += 1
            continue
        if m["doc_id"] in known:
            known[m["doc_id"]]["fuentes"].append({"url": it["source_url"], "cita": it["source_excerpt"]})
            dropped["conocido: duplicado (otra fuente del mismo fallo)"] += 1
            continue
        rv = reviews.get(it["key"], {"verdict": "keep", "fixed_query": "", "reason": "sin revisión"})
        if rv["verdict"] == "drop":
            dropped["conocido: descartado por el crítico"] += 1
            continue
        query = rv["fixed_query"] if rv["verdict"] == "fix" and rv["fixed_query"] else it["query"]
        if bad := leaks(query, cita, it["source_excerpt"], common):
            dropped[f"conocido: filtración ({', '.join(bad)})"] += 1
            continue
        uid = _id("k-", m["doc_id"])
        known[m["doc_id"]] = {
            "id": uid, "split": split(uid), "fuero": it["fuero"], "tipo_caso": it["tipo_caso"], "query": query,
            "cuestion": it["cuestion"], "decision": it["decision"], "favorece": it["favorece"], "doc_id": m["doc_id"],
            # the ruling is still the right answer to find; only the source's account of the outcome is off
            "decision_verificada": m["decision_coincide"], "nota_verificacion": m["nota"],
            "cita": cita, "fuentes": [{"url": it["source_url"], "cita": it["source_excerpt"]}],
            "revision": rv["reason"] if rv["verdict"] == "fix" else "",
        }
    queries, seen = [], set()
    for q in data["doctrine"]:
        rv = reviews.get(q["key"], {"verdict": "keep", "fixed_query": "", "fixed_relevante_si": "", "reason": ""})
        if rv["verdict"] == "drop":
            dropped["doctrina: descartada por el crítico"] += 1
            continue
        query = rv["fixed_query"] if rv["verdict"] == "fix" and rv["fixed_query"] else q["query"]
        if fold(query) in seen:
            dropped["doctrina: duplicada"] += 1
            continue
        seen.add(fold(query))
        uid = _id("q-", q["fuero"], fold(q["query"]))
        queries.append({
            "id": uid, "split": split(uid), "fuero": q["fuero"], "tipo_caso": q["tipo_caso"], "query": query,
            "cuestion": q["cuestion"], "relevante_si": rv.get("fixed_relevante_si") or q["relevante_si"],
            "no_relevante_si": q["no_relevante_si"], "lado_cliente": q["lado_cliente"], "fuentes": q["fuentes"],
            "revision": rv["reason"] if rv["verdict"] == "fix" else "",
        })
    return list(known.values()), queries, list(coverage.values()), dropped


def note_claims(data: dict, fuero_of: dict[str, str]) -> list[dict]:
    """What each human-written note says about a ruling we kept (read by agents that saw only the note)."""
    rows = list(data["validacion_existentes"])
    rows += [{**k["validacion"], "doc_id": k["match"]["doc_id"]} for k in data["known"]
             if k.get("validacion") and k["match"]["status"] == "found"]
    seen, out = set(), []
    for r in rows:
        if r["doc_id"] in fuero_of and r["doc_id"] not in seen:
            seen.add(r["doc_id"])
            out.append({**r, "fuero": fuero_of[r["doc_id"]]})
    return out


def _write(name: str, rows: list[dict]) -> None:
    with open(OUT / name, "w", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda r: (r["fuero"], r.get("id", ""))):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path, nargs="+", help="one workflow result per round, oldest first")
    rounds = [json.loads(path.read_text(encoding="utf-8")) for path in p.parse_args().results]
    data = {k: [x for r in rounds for x in r.get(k, [])] for k in ("known", "doctrine", "reviews", "validacion_existentes")}
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    df = Counter(w for (car,) in db.execute("SELECT caratula FROM documents WHERE active=1") for w in party_words(car))
    known, queries, coverage, dropped = build(data, {w for w, n in df.items() if n >= COMMON_DF})
    # independent check of each match: the passage the source quotes appears word for word in the ruling
    for r in known:
        texto = db.execute("SELECT texto FROM documents WHERE id=?", (r["doc_id"],)).fetchone()[0]
        r["cita_textual"] = any(copies(f["cita"], texto) for f in r["fuentes"])
    OUT.mkdir(parents=True, exist_ok=True)
    _write("known_items.jsonl", known)
    _write("queries.jsonl", queries)
    _write("cobertura.jsonl", coverage)
    _write("validacion_notas.jsonl", note_claims(data, {r["doc_id"]: r["fuero"] for r in known}))
    (OUT / "fuentes_workflow.json").write_text(json.dumps(rounds, ensure_ascii=False, indent=1), encoding="utf-8")

    table = defaultdict(Counter)
    for r in known:
        table[r["fuero"]][f"conocidos {r['split']}"] += 1
        table[r["fuero"]]["cita textual"] += r["cita_textual"]
    for r in queries:
        table[r["fuero"]][f"doctrina {r['split']}"] += 1
    for r in coverage:
        table[r["fuero"]]["citados"] += 1
        table[r["fuero"]]["en la base"] += r["status"] == "found"
    cols = ["conocidos dev", "conocidos test", "cita textual", "doctrina dev", "doctrina test", "citados",
            "en la base"]
    print(f"{'fuero':<18}" + "".join(f"{c:>16}" for c in cols))
    for fuero, c in sorted(table.items()):
        print(f"{fuero:<18}" + "".join(f"{c[k]:>16}" for k in cols))
    print("\ndescartados:")
    for reason, n in dropped.most_common():
        print(f"  {n:>4}  {reason}")


if __name__ == "__main__":
    main()
