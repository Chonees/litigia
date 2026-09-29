"""Scraper orchestration: how a day over the site cap is split (by tipo de oficina, then by oficina)."""

from datetime import date

import pytest

from scripts.catalog import Catalog
from scripts.scrapers.pjn_parse import CAP
from scripts.scrapers.pjn_tribunales import PJNScraper

DAY = date(2024, 3, 25)
SALA, JUZGADO = "3", "1"


class FakeSite:
    """A cámara whose offices are Salas (tipo 3) and juzgados (tipo 1), with `salas`/`juzgados` rulings per office."""

    def __init__(self, salas: dict, juzgados: dict):
        self.salas, self.juzgados = salas, juzgados
        self.searched: list[str] = []
        self.solver = type("Solver", (), {"cost": 0.0})()

    def oficinas(self, camara, tipo_oficina=""):
        if tipo_oficina == SALA:
            return [(t, t) for t in self.salas]
        if tipo_oficina == JUZGADO:
            return [(t, t) for t in self.juzgados]
        return [(t, t) for t in list(self.salas) + list(self.juzgados)]

    def search(self, jurisdiccion, camara, oficina, tipo, start, end, tipo_oficina=""):
        self.searched.append(oficina or f"{camara}/{tipo_oficina or '*'}")
        if oficina:
            n = {**self.salas, **self.juzgados}.get(oficina, 0)
            prefix = oficina
        elif tipo_oficina == SALA:
            n, prefix = sum(self.salas.values()), None
        elif tipo_oficina == JUZGADO:
            n, prefix = sum(self.juzgados.values()), None
        elif tipo_oficina:
            n, prefix = 0, None
        else:
            n, prefix = sum(self.salas.values()) + sum(self.juzgados.values()), None
        docs = self._docs(prefix, tipo_oficina)
        return n, docs[:CAP]

    def _docs(self, office, tipo_oficina):
        if office:
            return [{"uuid": f"{office}-{i}", "expediente": ""} for i in range({**self.salas, **self.juzgados}[office])]
        pool = {SALA: self.salas, JUZGADO: self.juzgados}.get(tipo_oficina, {**self.salas, **self.juzgados})
        return [{"uuid": f"{o}-{i}", "expediente": ""} for o, n in pool.items() for i in range(n)]


SALAS_127 = {"T_7_TS1": 0, "T_7_TS3": 24, "T_7_TS6": 46, "T_7_TS8": 19, "T_7_TSA": 38}
NO_JUZGADOS = {f"T_7_T{n:02d}": 0 for n in range(1, 81)}


@pytest.fixture
def make(tmp_path, monkeypatch):
    stored: list[str] = []
    monkeypatch.setattr(PJNScraper, "_store", lambda self, result, jur, tipo: stored.append(result["uuid"]))
    cats = []

    def _make(salas, juzgados):
        cat = Catalog(tmp_path / f"catalog{len(cats)}.db")
        cats.append(cat)
        site = FakeSite(salas, juzgados)
        return PJNScraper(cat, site, limit=10_000), site, cat, stored

    yield _make
    for c in cats:
        c.close()


def test_heavy_day_searches_salas_and_juzgados_as_two_groups(make):
    juzgados = dict(NO_JUZGADOS, T_7_T40=14, T_7_T24=12)      # 26 first-instance rulings
    s, site, _, stored = make(SALAS_127, juzgados)
    s.run("5-5", "C_7", "D", DAY, DAY)
    # 153 > CAP: Salas as a group (127 > CAP, so Sala by Sala) and juzgados as ONE search (26 ≤ CAP)
    assert "C_7/3" in site.searched and "C_7/1" in site.searched
    assert not any(t in site.searched for t in NO_JUZGADOS)
    assert set(SALAS_127) <= set(site.searched)
    assert {u for u in stored if u.startswith(("T_7_T40", "T_7_T24"))} == {f"T_7_T40-{i}" for i in range(14)} | {f"T_7_T24-{i}" for i in range(12)}


def test_group_under_the_cap_is_not_split_further(make):
    s, site, _, _ = make({"T_7_TS1": 60, "T_7_TS2": 50}, dict(NO_JUZGADOS, T_7_T01=5))
    s.run("5-5", "C_7", "D", DAY, DAY)
    assert "C_7/3" in site.searched                      # 110 Salas > CAP → Sala by Sala
    assert "C_7/1" in site.searched                      # 5 juzgados: one search
    assert "T_7_T01" not in site.searched


def test_juzgados_over_the_cap_are_split_one_by_one(make):
    juzgados = {f"T_7_T{n:02d}": 3 for n in range(1, 41)}   # 120 > CAP
    s, site, _, _ = make({"T_7_TS1": 10}, juzgados)
    s.run("5-5", "C_7", "D", DAY, DAY)
    assert set(juzgados) <= set(site.searched)


def test_an_interrupted_split_resumes_without_repeating_finished_groups(make):
    s, site, cat, _ = make(SALAS_127, dict(NO_JUZGADOS, T_7_T40=14))
    s.run("5-5", "C_7", "D", DAY, DAY)
    cat.db.execute("DELETE FROM searches WHERE key LIKE '%T_7_TSA%'")    # killed before the last Sala
    cat.db.commit()
    site.searched.clear()
    s.run("5-5", "C_7", "D", DAY, DAY)
    assert "T_7_TSA" in site.searched
    assert "T_7_TS3" not in site.searched     # already done
    assert "C_7/1" not in site.searched       # juzgados group already done
