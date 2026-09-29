"""Real data quality: cross-check each stored field against the ruling's own text (all rulings in range).

Coverage says a field exists; these checks say whether it is consistent with the source.
Usage (from backend/): python -m spikes.quality_check --desde 2025-09-27 --hasta 2026-09-27
"""

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import date

from scripts.config import settings

ENDINGS = re.compile(r"notif[ií]quese|reg[ií]strese|devu[ée]lvase|arch[ií]vese|c[oó]piese|hágase saber|oportunamente|"
                     r"JUEZ|JUEZA|SECRETARI|Ante m[ií]|cúmplase|vuelvan", re.IGNORECASE)


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def expediente_in_text(exp: str, text: str) -> bool:
    m = re.search(r"(\d+)/(\d{4})", exp or "")
    if not m:
        return False
    num, year = str(int(m.group(1))), m.group(2)
    digits = re.sub(r"[.\s]", "", text[:6000])
    return f"{num}/{year}" in digits or f"{num}/{year[2:]}" in digits


def expediente_contradicted(exp: str, text: str) -> bool:
    """The heading names a different case number (e.g. 'EXPEDIENTE Nº 7238/24' for a stored 5190/2025)."""
    m = re.search(r"(\d+)/(\d{4})", exp or "")
    if not m:
        return False
    head = re.sub(r"[.\s]", "", text[:800])
    found = re.findall(r"(?:EXPEDIENTE|EXPTE|CAUSA|CNT)[^0-9]{0,20}(\d{2,7})/(\d{2,4})", head, re.IGNORECASE)
    if not found:
        return False
    num, year = str(int(m.group(1))), m.group(2)
    return not any(str(int(n)) == num and (y == year or y == year[2:]) for n, y in found)


def first_party(caratula: str) -> str:
    words = re.findall(r"[A-ZÁÉÍÓÚÑ]{3,}", fold(caratula.split(" c/")[0].split(" C/")[0]))
    stop = {"LEGAJO", "INCIDENTE", "RECURSO", "QUEJA", "OTROS", "OTRO"}
    return next((w for w in words if w not in stop), "")


def surname(name: str) -> str:
    parts = [p for p in re.findall(r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]+", name) if len(p) > 2]
    return fold(parts[-1]) if parts else ""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--desde", required=True)
    p.add_argument("--hasta", required=True)
    a = p.parse_args()
    db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM documents WHERE source='pjn' AND active=1 AND tribunal LIKE '%TRABAJO%' "
        "AND fecha BETWEEN ? AND ? AND status<>'duplicate'", (a.desde, a.hasta))]
    fails: dict[str, list] = defaultdict(list)
    checks = Counter()
    by_inst = Counter()

    def check(name: str, ok: bool, r: dict) -> None:
        checks[name] += 1
        if not ok:
            fails[name].append((r["id"], r["caratula"][:60]))

    for r in rows:
        t, inst = r["texto"], r["instancia"] or "?"
        by_inst[inst] += 1
        head = fold(t[:6000])
        check("expediente: el texto no lo contradice", not expediente_contradicted(r["expediente"], t), r)
        check("expediente: confirmado en el texto (informativo)", expediente_in_text(r["expediente"], t), r)
        fp = first_party(r["caratula"])
        if fp:
            check("parte de la carátula aparece en el texto", fp in fold(t), r)
        d = date.fromisoformat(r["fecha"])
        check("fecha dentro del rango pedido", a.desde <= r["fecha"] <= a.hasta, r)
        check("fecha en día hábil (lun-vie)", d.weekday() < 5, r)
        check("el texto termina en parte resolutiva o firma", bool(ENDINGS.search(t[-1500:])), r)
        words = re.findall(r"\w+", t)
        garbage = sum(1 for w in words if len(w) > 25 or re.search(r"\d[a-záéíóú]\d", w)) / max(1, len(words))
        check("texto legible (sin basura de extracción)", garbage < 0.01, r)
        if inst == "camara":
            # the ruling names its own Sala in the heading ("SALA IX", "Sala VIII"); "Sala de Acuerdos" is not one
            own = re.findall(r"SALA\s+[\"“]?([IVX]+)\b", fold(t[:1500]))
            check("[cámara] Sala: el texto no la contradice", bool(r["sala"]) and (not own or r["sala"] in own), r)
            check("[cámara] Sala: confirmada en el texto (informativo)", r["sala"] in own, r)
            votos = json.loads(r["votos"])
            firm = {surname(f) for f in json.loads(r["firmantes"])}
            if votos and firm:
                check("[cámara] cada juez que vota también firma", all(surname(v) in firm for v in votos), r)
            check("[cámara] el texto se identifica como Cámara", "CAMARA" in head or "SALA" in head, r)
        elif inst == "primera":
            first = ("JUZGADO" in head or "JUEZ" in fold(t[-2000:])
                     or re.search(r"PROMUEVE|INICIA LA (PRESENTE )?(ACCION|DEMANDA)|FALLO\s*:|RESUELVO|SE PRESENTA", fold(t)) is not None)
            check("[primera] el texto es de primera instancia", first and "REUNIDOS EN LA SALA DE ACUERDOS" not in head, r)

    dup = Counter((r["expediente"], r["fecha"]) for r in rows)
    same_case_same_day = {k: v for k, v in dup.items() if v > 1}
    print(f"== {len(rows)} fallos · por instancia: {dict(by_inst)}\n")
    print(f"{'chequeo':52} {'ok':>8}   fallan")
    for name in checks:
        n, f = checks[name], len(fails[name])
        print(f"{name:52} {(n - f) / n:8.1%}   {f}")
    print(f"\nmismo expediente + misma fecha en más de un fallo: {len(same_case_same_day)} casos "
          f"({sum(same_case_same_day.values())} fallos)")
    print("\n-- ejemplos de lo que falla (para revisar a mano)")
    for name, items in fails.items():
        print(f"  {name}: {items[:3]}")
    json.dump({k: v for k, v in fails.items()}, open(settings.data_logs / "quality_check_fails.json", "w",
                                                     encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
