"""Audit a batch of freshly scraped rulings of one cámara against the current standards.

Usage (from backend/): python -m spikes.audit_batch --desde 2025-09-27 --hasta 2026-09-27 [--camara C_7]
Checks, on documents whose fecha falls in the range:
  - data contract: status and reasons, warnings
  - metadata completeness (fecha, tribunal, sala, carátula, expediente, firmantes)
  - enrichment coverage (objeto, resultado, normas, votos)
  - text quality (length, paragraphs, leftover noise)
  - duplicates and completeness against the totals the site reported
"""

import argparse
import json
import re
import sqlite3
import statistics
from collections import Counter

from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO

NOISE = {"sello de página": r"#\d+#\d+#\d+", "Fecha de firma": r"Fecha de firma:", "Firmado por": r"Firmado por:",
         # page-number sized only: longer numeric lines are table rows (amounts, dates), kept on purpose
         "número de página suelto": r"(?m)^\s*(?=[\d\s.:\-–]{1,8}\s*$)[\d\s.:\-–]*\d[\d\s.:\-–]*$"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True)
    p.add_argument("--hasta", required=True)
    p.add_argument("--camara", default="C_7", choices=list(CAMARA_FUERO))
    a = p.parse_args()
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM documents WHERE source='pjn' AND active=1 AND fecha BETWEEN ? AND ? "
        "AND fuero=?", (a.desde, a.hasta, CAMARA_FUERO[a.camara]))]
    if not rows:
        print("sin documentos en el rango todavía")
        return
    from scripts.enrich import detect_instancia
    groups = {}
    for r in rows:
        groups.setdefault(detect_instancia(r["tribunal"]) or "?", []).append(r)
    print(f"== {len(rows)} fallos {a.camara} ({CAMARA_FUERO[a.camara]}) {a.desde}..{a.hasta} · por instancia: "
          + ", ".join(f"{k} {len(v)}" for k, v in groups.items()))
    for inst, group in sorted(groups.items()):
        report(db, inst, group, a)
    completeness(db, rows, a)


def report(db, inst: str, rows: list, a) -> None:
    n = len(rows)
    pct = lambda k: f"{k / n:.1%}"
    print(f"\n######## instancia: {inst} ({n} fallos)")
    st = Counter(r["status"] for r in rows)
    print("estado:", dict(st), f"· indexables {pct(st['indexable'])}")
    print("motivos:", dict(Counter(x.split(':')[0] for r in rows for x in json.loads(r["reasons"]))))
    print("advertencias:", dict(Counter(x for r in rows for x in json.loads(r["warnings"]))))

    print("\n-- metadatos")
    for f in ("fecha", "tribunal", "sala", "caratula", "expediente"):
        ok = sum(1 for r in rows if r[f] and not (f == "caratula" and r[f] == r["expediente"]))
        print(f"  {f:11} {pct(ok)}")
    print(f"  firmantes   {pct(sum(1 for r in rows if json.loads(r['firmantes'])))}")
    print("  salas:", Counter(r["sala"] for r in rows).most_common())

    print("\n-- enriquecimiento")
    for f in ("objeto", "resultado", "normas", "votos", "numero"):
        print(f"  {f:10} {pct(sum(1 for r in rows if r[f] not in ('', '[]', None)))}")
    print("  resultado:", Counter(r["resultado"] or "?" for r in rows).most_common())
    print("  objeto top:", Counter(r["objeto"] for r in rows).most_common(6))

    print("\n-- texto")
    ch = sorted(r["chars"] for r in rows)
    pars = sorted(len(r["texto"].split("\n\n")) for r in rows)
    print(f"  caracteres p10/p50/p90: {ch[n // 10]} / {ch[n // 2]} / {ch[9 * n // 10]}")
    print(f"  párrafos   p10/p50/p90: {pars[n // 10]} / {pars[n // 2]} / {pars[9 * n // 10]}")
    for name, pat in NOISE.items():
        print(f"  ruido '{name}': {sum(1 for r in rows if re.search(pat, r['texto']))} fallos")


def completeness(db, rows: list, a) -> None:
    n = len(rows)
    st = Counter(r["status"] for r in rows)
    print("\n-- duplicados y completitud (todas las instancias)")
    print("  textos idénticos entre fallos activos:",
          n - len({r["text_hash"] for r in rows}), "· duplicate:", st.get("duplicate", 0))
    # Completeness per finished cámara-level search: what the site reported vs. what the catalog holds
    # for those dates. A truncated day stays "en curso" until its oficina split covers the total.
    leaves = db.execute(
        "SELECT key, total, truncated FROM searches WHERE source='pjn' AND split=0 AND key LIKE ? "
        "AND substr(key, -21, 10) >= ? AND substr(key, -10) <= ?", (f"5-5|{a.camara}|*|%", a.desde, a.hasta)).fetchall()
    site = have = complete = in_progress = lost = 0
    for key, total, truncated in leaves:
        s, e = key.split("|")[-2:]
        n_docs = db.execute("SELECT COUNT(*) FROM documents WHERE source='pjn' AND fuero=? "
                            "AND fecha BETWEEN ? AND ?", (CAMARA_FUERO[a.camara], s, e)).fetchone()[0]
        site += total
        have += min(n_docs, total)
        if n_docs >= total:
            complete += 1
        elif truncated:
            in_progress += 1
        else:
            lost += 1
    print(f"  tramos terminados {len(leaves)} · completos {complete} · partiéndose por Sala {in_progress} · "
          f"INCOMPLETOS {lost} · el sitio informó {site} · en catálogo {have} ({have / max(site, 1):.1%})")
    rate = statistics.mean(1 if r["fecha"] else 0 for r in rows)
    print(f"  (fechas presentes {rate:.0%})")


if __name__ == "__main__":
    main()
