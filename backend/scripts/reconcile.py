"""Accounting per cámara: every ruling the site reported, and what happened to it.

For each finished cámara-level search (a leaf of the date split):
  sitio        rulings the site reported for those dates
  listados     distinct rulings it actually listed (every page, every office split of those dates)
  guardados    listed rulings stored with text
  fallidos     listed rulings whose PDF failed (table `failures`, with the reason)
  pendientes   listed but neither stored nor failed (e.g. the run stopped at --limit)
  no listados  sitio − listados (pagination gaps such as "only 80 of 84")
  fecha fuera  stored rulings whose fecha is outside the dates they were listed under
  por fecha    active rulings of the fuero with a fecha in those dates (the only measure for
               searches made before listings were recorded)
  sin listado  searches with results but no recorded listing (made before this accounting existed)
Plus the days of the range that no finished search covers.

Usage (from backend/): python -m scripts.reconcile --camara C_1 --desde 2026-08-01 --hasta 2026-09-27 [--check-site]
"""

import argparse
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import date, timedelta

from scripts.config import settings
from scripts.scrapers.pjn_tribunales import CAMARA_FUERO

COLUMNS = ["sitio", "listados", "guardados", "fallidos", "pendientes", "no_listados", "fecha_fuera", "por_fecha",
           "sin_listado"]


@dataclass
class Leaf:
    start: str
    end: str
    sitio: int = 0
    listados: int = 0
    guardados: int = 0
    fallidos: int = 0
    pendientes: int = 0
    fecha_fuera: int = 0
    por_fecha: int = 0
    sin_listado: int = 0
    no_listados: int = 0

    def add(self, other: "Leaf") -> None:
        for f in fields(self):
            if isinstance(getattr(self, f.name), int):
                setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))


def _dates(key: str) -> tuple[str, str]:
    s, e = key.split("|")[-2:]
    return s, e


def _days(s: str, e: str):
    d, end = date.fromisoformat(s), date.fromisoformat(e)
    while d <= end:
        yield d
        d += timedelta(days=1)


def accounts(db: sqlite3.Connection, camara: str, desde: date, hasta: date,
             jur: str = "5-5", tipo: str = "D") -> tuple[list[Leaf], list[date]]:
    lo, hi = desde.isoformat(), hasta.isoformat()
    # Two runs over the same days (a pilot at home, then a VPS) split them differently: keep the most recent
    # search and drop any older one that overlaps it, so no day is counted twice.
    found = []
    for key, total, at in db.execute(
            "SELECT key, total, at FROM searches WHERE source='pjn' AND split=0 AND key LIKE ?",
            (f"{jur}|{camara}|*|{tipo}|%",)):
        s, e = _dates(key)
        if s >= lo and e <= hi:
            found.append((at or "", s, e, total or 0))
    leaves: list[Leaf] = []
    for _, s, e, total in sorted(found, reverse=True):
        if not any(s <= l.end and l.start <= e for l in leaves):
            leaves.append(Leaf(s, e, sitio=total))
    leaves.sort(key=lambda l: l.start)

    listed: dict[int, set] = defaultdict(set)
    for key, sid in db.execute("SELECT key, source_id FROM listings WHERE source='pjn' AND key LIKE ?",
                               (f"{jur}|{camara}|%|{tipo}|%",)):
        s, e = _dates(key)
        for i, leaf in enumerate(leaves):
            if leaf.start <= s and e <= leaf.end:
                listed[i].add(sid)
                break

    ids = set().union(*listed.values()) if listed else set()
    docs = {}
    failed = set()
    if ids:
        for sid, fecha, chars in db.execute("SELECT source_id, fecha, chars FROM documents WHERE source='pjn'"):
            if sid in ids:
                docs[sid] = (fecha or "", chars or 0)
        failed = {r[0] for r in db.execute("SELECT source_id FROM failures WHERE source='pjn'")} & ids

    per_day = Counter(dict(db.execute(
        "SELECT fecha, COUNT(*) FROM documents WHERE source='pjn' AND active=1 AND fuero=? GROUP BY fecha",
        (CAMARA_FUERO.get(camara, ""),)).fetchall()))

    for i, leaf in enumerate(leaves):
        for sid in listed.get(i, ()):
            leaf.listados += 1
            fecha, chars = docs.get(sid, ("", 0))
            if chars:
                leaf.guardados += 1
                if not (leaf.start <= fecha <= leaf.end):
                    leaf.fecha_fuera += 1
            elif sid in failed:
                leaf.fallidos += 1
            else:
                leaf.pendientes += 1
        leaf.por_fecha = sum(per_day.get(d.isoformat(), 0) for d in _days(leaf.start, leaf.end))
        if leaf.sitio and not leaf.listados:
            leaf.sin_listado = 1          # unknown: searched before listings were recorded
        else:
            leaf.no_listados = max(leaf.sitio - leaf.listados, 0)

    covered = {d for leaf in leaves for d in _days(leaf.start, leaf.end)}
    uncovered = [d for d in _days(lo, hi) if d not in covered]
    return leaves, uncovered


def by_period(leaves: list[Leaf], period: str = "month") -> dict[str, Leaf]:
    """Leaves added up by the month (YYYY-MM) or year (YYYY) they start in."""
    width = 7 if period == "month" else 4
    out: dict[str, Leaf] = {}
    for leaf in leaves:
        p = leaf.start[:width]
        out.setdefault(p, Leaf(p, p)).add(leaf)
    return dict(sorted(out.items()))


def _ranges(days: list[date]) -> str:
    if not days:
        return "ninguno"
    out, start, prev = [], days[0], days[0]
    for d in days[1:] + [None]:
        if d is None or d != prev + timedelta(days=1):
            out.append(f"{start}" if start == prev else f"{start}..{prev}")
            if d is not None:
                start = d
        prev = d if d is not None else prev
    return ", ".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="Conciliación sitio vs catálogo, por mes y por año")
    p.add_argument("--camara", required=True, choices=list(CAMARA_FUERO))
    p.add_argument("--desde", type=date.fromisoformat, required=True)
    p.add_argument("--hasta", type=date.fromisoformat, required=True)
    p.add_argument("--tipo", default="D")
    p.add_argument("--check-site", action="store_true", help="also ask the site once for the whole range")
    a = p.parse_args()
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    leaves, uncovered = accounts(db, a.camara, a.desde, a.hasta, tipo=a.tipo)
    print(f"== {a.camara} ({CAMARA_FUERO[a.camara]}) · tipo {a.tipo} · {a.desde}..{a.hasta} · {len(leaves)} búsquedas terminadas\n")
    head = f"{'período':<9}" + "".join(f"{c.replace('_', ' '):>12}" for c in COLUMNS)
    for period in ("month", "year"):
        print(head)
        for name, t in by_period(leaves, period).items():
            print(f"{name:<9}" + "".join(f"{getattr(t, c):>12,}" for c in COLUMNS))
        print()
    total = Leaf("", "")
    for leaf in leaves:
        total.add(leaf)
    if total.listados:
        print(f"De lo que listó el sitio: guardados {total.guardados / total.listados:.1%} · "
              f"fallidos {total.fallidos / total.listados:.1%} · pendientes {total.pendientes / total.listados:.1%}")
    if total.sin_listado:
        print(f"{total.sin_listado} búsquedas son anteriores a esta contabilidad: para ellas solo vale 'por fecha'.")
    if total.sitio:
        print(f"Del total del sitio: listados {total.listados / total.sitio:.1%} · "
              f"en catálogo por fecha {min(total.por_fecha, total.sitio) / total.sitio:.1%}")
    print(f"Días sin ninguna búsqueda terminada: {_ranges(uncovered)}")
    reasons = db.execute(
        "SELECT reason, COUNT(*) FROM failures WHERE source='pjn' AND key LIKE ? GROUP BY reason",
        (f"5-5|{a.camara}|%",)).fetchall()
    if reasons:
        print("Motivos de falla:", dict(reasons))
    if a.check_site:
        from scripts.scrapers.pjn_tribunales import CaptchaSolver, site_total
        n = site_total(CaptchaSolver(), a.camara, a.tipo, a.desde, a.hasta)
        print(f"El sitio, en una sola búsqueda de todo el rango: {n} · suma de las búsquedas: {total.sitio}")


if __name__ == "__main__":
    main()
