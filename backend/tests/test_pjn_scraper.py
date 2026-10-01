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

    def search(self, jurisdiccion, camara, oficina, tipo, start, end, tipo_oficina="", expediente=""):
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
    monkeypatch.setattr(PJNScraper, "_store", lambda self, result, jur, tipo, key="": stored.append(result["uuid"]))
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


def test_a_failed_pdf_still_waits_before_the_next_request(tmp_path, monkeypatch):
    """An empty PDF must not turn the loop into back-to-back requests (2026-09-29: 10 in one second)."""
    import scripts.scrapers.pjn_tribunales as pjn
    waits: list[float] = []
    monkeypatch.setattr(pjn.time, "sleep", waits.append)
    monkeypatch.setattr(pjn, "_get", lambda client, method, url, **kw: type("R", (), {"content": b""})())
    cat = Catalog(tmp_path / "catalog.db")
    s = PJNScraper(cat, FakeSite({}, {}), limit=10)
    s._store({"uuid": "u1", "expediente": "CIV 1/2022", "pdf_url": "https://x/1.pdf",
              "tribunal": "", "caratula": "", "fecha": ""}, "5-5", "D", key="k")
    failure = cat.db.execute("SELECT reason, key, url FROM failures WHERE source_id='u1'").fetchone()
    cat.close()
    assert s.errors == 1
    assert waits == [pjn.REQUEST_DELAY]
    assert tuple(failure) == ("EmptyFileError", "k", "https://x/1.pdf")


def test_a_pdf_that_downloads_later_clears_its_failure(tmp_path, monkeypatch):
    import scripts.scrapers.pjn_tribunales as pjn
    from tests.test_catalog import LONG
    monkeypatch.setattr(pjn.time, "sleep", lambda s: None)
    monkeypatch.setattr(pjn, "_get", lambda client, method, url, **kw: type("R", (), {"content": b"%PDF"})())
    monkeypatch.setattr(pjn, "extract_pdf_text", lambda content: LONG)
    cat = Catalog(tmp_path / "catalog.db")
    cat.record_failure("pjn", "u1", url="https://x/1.pdf", key="k", reason="EmptyFileError")
    s = PJNScraper(cat, FakeSite({}, {}), limit=10)
    s._store({"uuid": "u1", "expediente": "CIV 1/2022", "pdf_url": "https://x/1.pdf",
              "tribunal": "CAMARA CIVIL - SALA C", "caratula": "A c/ B s/ daños", "fecha": "2026-08-03"}, "5-5", "D", key="k")
    left = cat.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
    cat.close()
    assert (s.new, left) == (1, 0)


def test_every_listed_result_is_recorded_under_its_search(make):
    s, site, cat, _ = make({"T_7_TS1": 30}, {"T_7_T01": 12})
    s.run("5-5", "C_7", "D", DAY, DAY)
    listed = cat.db.execute("SELECT key, COUNT(*) FROM listings GROUP BY key").fetchall()
    assert dict(listed) == {f"5-5|C_7|*|D|{DAY}|{DAY}": 42}


def test_office_by_office_stops_once_the_group_total_is_covered(make):
    # 2026-08-03, seguridad social: Salas 117 > CAP; Sala 1 (76) + Sala 3 (41) already cover it
    salas = {"T_5_GS1": 76, "T_5_GS2": 0, "T_5_GS3": 41, "T_5_GS3_HON": 0, "T_5_GS4": 0}
    s, site, _, _ = make(salas, {"T_5_J1": 20})
    s.run("5-5", "C_5", "D", DAY, DAY)
    assert {"T_5_GS1", "T_5_GS3"} <= set(site.searched)
    assert "T_5_GS3_HON" not in site.searched and "T_5_GS4" not in site.searched


class YearSite:
    """Seguridad social, 2026-08-04: Sala 1 alone has 147 rulings that day, over the site's CAP.

    Its search accepts part of a case number, so "/2021" returns only the 2021 cases.
    """

    def __init__(self, years: dict):
        self.years = years                      # {year: rulings} in T_5_GS1 that day
        self.searched: list[str] = []
        self.solver = type("Solver", (), {"cost": 0.0})()

    def oficinas(self, camara, tipo_oficina=""):
        return [("T_5_GS1", "Sala 1")]

    def search(self, jurisdiccion, camara, oficina, tipo, start, end, tipo_oficina="", expediente=""):
        self.searched.append((oficina or f"{camara}/{tipo_oficina or '*'}") + expediente)
        docs = [{"uuid": f"{y}-{i}", "expediente": f"CSS {i:06d}/{y}/CA001"} for y, n in self.years.items() for i in range(n)]
        if expediente:
            docs = [d for d in docs if expediente in d["expediente"]]
        return len(docs), docs[:CAP]


def test_one_office_over_the_cap_in_one_day_is_split_by_case_year(tmp_path, monkeypatch):
    stored: list[str] = []
    monkeypatch.setattr(PJNScraper, "_store", lambda self, result, jur, tipo, key="": stored.append(result["uuid"]))
    cat = Catalog(tmp_path / "catalog.db")
    site = YearSite({DAY.year: 60, 2021: 50, 2014: 37})              # a case can't be newer than its ruling
    PJNScraper(cat, site, limit=10_000).run("5-5", "C_5", "D", DAY, DAY)
    cat.close()
    assert len(set(stored)) == 147                                  # nothing lost to the 100 cap
    assert "T_5_GS1/2014" in site.searched
    assert "T_5_GS1/2013" not in site.searched                      # stops once the 147 are covered


def test_case_years_seen_in_the_first_results_are_searched_first(tmp_path, monkeypatch):
    # The first 100 results already show which case years are common; the rest are rare old years.
    monkeypatch.setattr(PJNScraper, "_store", lambda self, result, jur, tipo, key="": None)
    cat = Catalog(tmp_path / "catalog.db")
    site = YearSite({2021: 60, 2016: 45, 2009: 1})                 # first 100 results: 2021 ×60, 2016 ×40
    PJNScraper(cat, site, limit=10_000).run("5-5", "C_5", "D", DAY, DAY)
    cat.close()
    years = [s.split("/")[1] for s in site.searched if s.startswith("T_5_GS1/")]
    assert years[:2] == ["2021", "2016"]                            # the common years first, most frequent first
    assert "2009" in years                                          # then the unseen years, until the total is covered
