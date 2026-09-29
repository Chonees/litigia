from scripts.audit import compare, summarize
from scripts.catalog import Catalog
from tests.test_catalog import doc


def test_summarize_reports_quality_and_completeness(tmp_path):
    cat = Catalog(tmp_path / "c.db")
    cat.upsert(doc("a1"))
    cat.upsert(doc("b2", fecha=""))
    cat.upsert(doc("c3", texto="Téngase presente."))
    cat.record_search("pjn", "k1", total=30, fetched=3, split=False, truncated=False)
    cat.record_search("pjn", "k2", total=55, fetched=40, split=False, truncated=True)

    s = summarize(cat)["pjn"]
    cat.close()

    assert s["documents"] == 3
    assert s["status"] == {"indexable": 1, "pending": 1, "rejected": 1}
    assert s["indexable_pct"] == 33.3
    assert s["reasons"]["sin_fecha"] == 1
    assert s["reasons"]["texto_corto"] == 1
    assert s["by_fuero_year"] == {"laboral": {"2024": 1}}
    assert s["searches"] == {"leaves": 2, "reported": 85, "fetched": 43, "completeness_pct": 50.6, "truncated": 1}


def test_compare_shows_what_changed_since_last_audit():
    before = {"pjn": {"documents": 10, "indexable_pct": 50.0, "status": {"indexable": 5}}}
    after = {"pjn": {"documents": 30, "indexable_pct": 60.0, "status": {"indexable": 18}}}
    assert compare(before, after) == {"pjn": {"documents": 20, "indexable": 13, "indexable_pct": 10.0}}


def test_summarize_counts_only_active_documents(tmp_path):
    cat = Catalog(tmp_path / "c.db")
    cat.upsert(doc("a1"))
    cat.upsert(doc("b2", texto=doc()["texto"] + " otro"))
    cat.disable("source_id = ?", ("b2",), reason="scraper_viejo")
    s = summarize(cat)["pjn"]
    cat.close()
    assert s["documents"] == 1
    assert s["disabled"] == 1
