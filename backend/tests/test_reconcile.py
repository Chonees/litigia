"""Accounting per cámara: site totals vs listed vs stored vs failed, per finished search."""

from datetime import date

import pytest

from scripts.catalog import Catalog
from scripts.reconcile import accounts, by_period
from tests.test_catalog import doc

CIVIL = "CAMARA CIVIL - SALA C"


@pytest.fixture
def cat(tmp_path):
    c = Catalog(tmp_path / "catalog.db")
    yield c
    c.close()


def search(cat, key, total, truncated=False):
    cat.record_search("pjn", key, total=total, fetched=min(total, 100), split=False, truncated=truncated)


def test_a_leaf_accounts_for_every_ruling_the_site_reported(cat):
    key = "5-5|C_1|*|D|2026-08-01|2026-08-04"
    search(cat, key, total=5)
    cat.record_listing("pjn", key, ["a", "b", "c", "d"])                  # the site listed 4 of its 5
    cat.upsert(doc("a", fecha="2026-08-02", tribunal=CIVIL))
    cat.upsert(doc("b", fecha="2026-07-30", tribunal=CIVIL))              # stored with a date outside its search
    cat.record_failure("pjn", "c", url="u", key=key, reason="EmptyFileError")
    # d: listed, neither stored nor failed (the run stopped)
    leaves, uncovered = accounts(cat.db, "C_1", date(2026, 8, 1), date(2026, 8, 4))
    (leaf,) = leaves
    assert (leaf.sitio, leaf.listados, leaf.guardados, leaf.fallidos, leaf.pendientes, leaf.no_listados) == (5, 4, 2, 1, 1, 1)
    assert leaf.fecha_fuera == 1
    assert uncovered == []


def test_office_splits_of_a_heavy_day_count_toward_that_day(cat):
    day = "5-5|C_1|*|D|2026-08-05|2026-08-05"
    search(cat, day, total=3, truncated=True)
    search(cat, "5-5|C_1|*3|D|2026-08-05|2026-08-05", total=2)            # Salas as a group
    cat.record_listing("pjn", "5-5|C_1|*3|D|2026-08-05|2026-08-05", ["s1", "s2"])
    cat.record_listing("pjn", "5-5|C_1|T_1_J5|D|2026-08-05|2026-08-05", ["j1"])
    leaves, _ = accounts(cat.db, "C_1", date(2026, 8, 5), date(2026, 8, 5))
    assert [(l.sitio, l.listados) for l in leaves] == [(3, 3)]            # the group search is not a second leaf


def test_days_no_finished_search_covers_are_reported(cat):
    search(cat, "5-5|C_1|*|D|2026-08-01|2026-08-02", total=0)
    _, uncovered = accounts(cat.db, "C_1", date(2026, 8, 1), date(2026, 8, 4))
    assert uncovered == [date(2026, 8, 3), date(2026, 8, 4)]


def test_other_camaras_and_tipos_are_ignored(cat):
    search(cat, "5-5|C_7|*|D|2026-08-01|2026-08-04", total=9)
    search(cat, "5-5|C_1|*|I|2026-08-01|2026-08-04", total=9)
    leaves, _ = accounts(cat.db, "C_1", date(2026, 8, 1), date(2026, 8, 4))
    assert leaves == []


def test_legacy_searches_without_listings_fall_back_to_counting_by_date(cat):
    search(cat, "5-5|C_1|*|D|2026-08-01|2026-08-04", total=2)
    cat.upsert(doc("a", fecha="2026-08-03", tribunal=CIVIL))
    (leaf,), _ = accounts(cat.db, "C_1", date(2026, 8, 1), date(2026, 8, 4))
    assert (leaf.listados, leaf.por_fecha) == (0, 1)
    assert (leaf.no_listados, leaf.sin_listado) == (0, 1)     # unknown, not 'the site did not list them'


def test_periods_add_up_leaves_by_the_month_they_start(cat):
    for key, total in [("5-5|C_1|*|D|2026-07-30|2026-08-02", 4), ("5-5|C_1|*|D|2026-08-03|2026-08-04", 6)]:
        search(cat, key, total=total)
    leaves, _ = accounts(cat.db, "C_1", date(2026, 7, 30), date(2026, 8, 4))
    assert {p: t.sitio for p, t in by_period(leaves, "month").items()} == {"2026-07": 4, "2026-08": 6}
    assert by_period(leaves, "year")["2026"].sitio == 10


def test_overlapping_searches_from_two_runs_are_not_counted_twice(cat):
    # pilot from home split Aug 1-7 one way; a VPS later split the same days another way
    search(cat, "5-5|C_10|*|D|2026-08-01|2026-08-07", total=10)       # pilot (older)
    cat.db.execute("UPDATE searches SET at='2026-09-29 17:00:00'")
    cat.db.commit()
    search(cat, "5-5|C_10|*|D|2026-08-01|2026-08-04", total=6)        # VPS (newer)
    search(cat, "5-5|C_10|*|D|2026-08-05|2026-08-07", total=4)
    leaves, uncovered = accounts(cat.db, "C_10", date(2026, 8, 1), date(2026, 8, 7))
    assert sum(l.sitio for l in leaves) == 10
    assert uncovered == []
