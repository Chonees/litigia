import io
import tarfile
from datetime import date

from scripts.catalog import Catalog
from scripts.scrapers.deploy_parallel import merge_catalog, package_scripts, split_range
from tests.test_catalog import LONG, doc


def test_split_range_covers_every_day_once():
    parts = split_range(date(2025, 9, 27), date(2026, 9, 27), 10)
    assert len(parts) == 10
    assert parts[0][0] == date(2025, 9, 27) and parts[-1][1] == date(2026, 9, 27)
    for (_, e), (s, _) in zip(parts, parts[1:]):
        assert (s - e).days == 1
    sizes = [(e - s).days + 1 for s, e in parts]
    assert sum(sizes) == 366 and max(sizes) - min(sizes) <= 1


def test_split_range_never_returns_empty_parts():
    parts = split_range(date(2026, 1, 1), date(2026, 1, 3), 10)
    assert parts == [(date(2026, 1, 1), date(2026, 1, 1)), (date(2026, 1, 2), date(2026, 1, 2)),
                     (date(2026, 1, 3), date(2026, 1, 3))]


def test_package_contains_the_scraper_but_no_caches_or_secrets():
    names = tarfile.open(fileobj=io.BytesIO(package_scripts()), mode="r:gz").getnames()
    assert "scripts/scrapers/pjn_tribunales.py" in names
    assert "scripts/catalog.py" in names
    assert not any("__pycache__" in n or n.endswith(".env") for n in names)


def test_merge_catalog_copies_documents_and_searches(tmp_path):
    remote = Catalog(tmp_path / "remote.db")
    remote.upsert(doc("r1", texto=LONG + " uno"))
    remote.upsert(doc("r2", texto=LONG + " dos"))
    remote.record_search("pjn", "5-5|C_7|*|D|2026-01-01|2026-01-01", total=2, fetched=2, split=False, truncated=False)
    remote.close()

    local = Catalog(tmp_path / "local.db")
    local.upsert(doc("r1", texto=LONG + " uno"))       # already present: must not duplicate
    stats = merge_catalog(tmp_path / "remote.db", local)
    assert stats == {"documents": 2, "new": 1, "searches": 1}
    assert local.count() == 2
    assert local.get("pjn", "r2")["status"] == "indexable"
    assert local.search_done("pjn", "5-5|C_7|*|D|2026-01-01|2026-01-01")
    # idempotent
    assert merge_catalog(tmp_path / "remote.db", local)["new"] == 0
    local.close()
