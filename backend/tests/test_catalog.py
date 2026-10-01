import pytest

from scripts.catalog import Catalog

LONG = "\n\n".join(
    f"{n}.- La cuestión traída a conocimiento del Tribunal exige analizar el art. 80 de la "
    "Ley de Contrato de Trabajo y la jurisprudencia aplicable al caso concreto. " * 3
    for n in ("I", "II", "III", "IV")
)


def doc(source_id="a1", **overrides):
    d = {
        "source": "pjn",
        "source_id": source_id,
        "url": f"https://example/{source_id}.pdf",
        "texto": LONG + f"\n\nExpediente {source_id}.",
        "fecha": "2024-12-30",
        "tribunal": "CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA I",
        "caratula": "OLMEDO c/ GALENO ART S.A. s/RECURSO LEY 27348",
        "expediente": "CNT 044625/2024/CA001",
        "jurisdiccion": "Ciudad de Buenos Aires",
        "tipo_fallo": "D",
        "firmantes": ["JUEZ UNO", "JUEZ DOS"],
    }
    d.update(overrides)
    return d


@pytest.fixture
def cat(tmp_path):
    c = Catalog(tmp_path / "catalog.db")
    yield c
    c.close()


def test_upsert_stores_assessment_and_derived_fields(cat):
    assert cat.upsert(doc()) == "indexable"
    row = cat.get("pjn", "a1")
    assert row["fuero"] == "laboral"
    assert row["sala"] == "I"
    assert row["firmantes"] == ["JUEZ UNO", "JUEZ DOS"]
    assert row["chars"] > 1500
    assert cat.has("pjn", "a1")
    assert not cat.has("pjn", "zzz")


def test_same_source_id_twice_is_one_row(cat):
    cat.upsert(doc())
    cat.upsert(doc())
    assert cat.count() == 1


def test_upsert_fills_missing_metadata_without_erasing(cat):
    cat.upsert(doc(fecha="", caratula=""))
    assert cat.get("pjn", "a1")["status"] == "pending"
    cat.upsert({"source": "pjn", "source_id": "a1", "fecha": "2024-12-30", "caratula": "X c/ Y s/ despido"})
    row = cat.get("pjn", "a1")
    assert row["status"] == "indexable"
    assert row["texto"].startswith("I.-")


def test_same_text_under_another_id_is_a_duplicate(cat):
    cat.upsert(doc("a1"))
    status = cat.upsert(doc("b2", texto=doc("a1")["texto"]))
    assert status == "duplicate"
    assert cat.get("pjn", "b2")["reasons"] == [f"duplicado_de:{cat.get('pjn', 'a1')['id']}"]


def test_record_search_and_resume(cat):
    cat.record_search("pjn", "5-5|C_7|D|2024-03-01|2024-03-31", total=372, fetched=0, split=True, truncated=False)
    cat.record_search("pjn", "5-5|C_7|D|2024-03-01|2024-03-02", total=24, fetched=24, split=False, truncated=False)
    assert cat.search_done("pjn", "5-5|C_7|D|2024-03-01|2024-03-02")
    assert not cat.search_done("pjn", "5-5|C_7|D|2024-03-01|2024-03-31")


def test_reassess_applies_the_current_contract(cat, monkeypatch):
    cat.upsert(doc())
    import scripts.quality as quality
    monkeypatch.setattr(quality, "MIN_CHARS", 10_000_000)
    counts = cat.reassess()
    assert counts == {"rejected": 1}
    assert cat.get("pjn", "a1")["reasons"] == ["texto_corto"]


def test_a_long_reader_does_not_block_the_scraper(tmp_path):
    # The audit reads the whole catalog while the scraper keeps writing.
    import sqlite3

    writer = Catalog(tmp_path / "catalog.db", busy_timeout=0.5)
    for i in range(300):
        writer.upsert(doc(source_id=f"a{i}", texto=LONG + f" variante {i}"))
    reader = sqlite3.connect(tmp_path / "catalog.db", timeout=0.1)
    cursor = reader.execute("SELECT * FROM documents")
    cursor.fetchone()                      # read transaction stays open
    writer.upsert(doc(source_id="b"))      # must not raise "database is locked"
    writer.record_search("pjn", "k", total=1, fetched=1, split=False, truncated=False)
    reader.close()
    assert writer.count() == 301
    writer.close()


def test_upsert_stores_enrichment(cat):
    cat.upsert(doc(caratula="SOSA c/ ACME S.A. s/DESPIDO",
                   texto=LONG + "\n\nPor ello, el Tribunal RESUELVE: 1) Confirmar la sentencia (ley 24.557)."))
    row = cat.get("pjn", "a1")
    assert row["objeto"] == "DESPIDO"
    assert row["resultado"] == "confirma"
    assert "ley 24.557" in row["normas"]


def test_upsert_drops_page_number_paragraphs(cat):
    cat.upsert(doc(texto=LONG + "\n\n2\n\nPor ello, el Tribunal RESUELVE: 1) Confirmar."))
    assert "\n\n2\n\n" not in cat.get("pjn", "a1")["texto"]


def test_old_catalog_gets_the_new_columns(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, source TEXT, source_id TEXT, texto TEXT, "
                "UNIQUE(source, source_id))")
    old.commit(); old.close()
    c = Catalog(path)
    cols = {r[1] for r in c.db.execute("PRAGMA table_info(documents)")}
    assert {"objeto", "resultado", "normas", "numero", "votos", "por_mayoria"} <= cols
    c.close()


def test_disable_keeps_the_row_but_marks_it_inactive(cat):
    cat.upsert(doc("old1"))
    cat.upsert(doc("new1", texto=LONG + " nuevo"))
    n = cat.disable("source_id = ?", ("old1",), reason="scraper_viejo")
    assert n == 1
    assert cat.get("pjn", "old1")["active"] == 0
    assert cat.get("pjn", "old1")["disabled_reason"] == "scraper_viejo"
    assert cat.get("pjn", "new1")["active"] == 1
    assert cat.count() == 2
    assert cat.count(active_only=True) == 1


def test_reassess_does_not_reactivate(cat):
    cat.upsert(doc("old1"))
    cat.disable("source_id = ?", ("old1",), reason="scraper_viejo")
    cat.reassess()
    assert cat.get("pjn", "old1")["active"] == 0


def test_a_fresh_scrape_reactivates_the_document(cat):
    cat.upsert(doc("old1"))
    cat.disable("source_id = ?", ("old1",), reason="scraper_viejo")
    cat.upsert({"source": "pjn", "source_id": "old1", "caratula": "SOSA c/ ACME s/DESPIDO"})
    row = cat.get("pjn", "old1")
    assert row["active"] == 1 and row["disabled_reason"] == ""


def test_enable_undoes_disable(cat):
    cat.upsert(doc("old1"))
    cat.disable("source_id = ?", ("old1",), reason="scraper_viejo")
    assert cat.enable("disabled_reason = ?", ("scraper_viejo",)) == 1
    assert cat.get("pjn", "old1")["active"] == 1


def test_merge_from_another_catalog_brings_documents_and_searches(tmp_path):
    main = Catalog(tmp_path / "main.db")
    main.upsert(doc("shared", texto=LONG + " version local"))
    remote = Catalog(tmp_path / "vps.db")
    remote.upsert(doc("r1", texto=LONG + " uno"))
    remote.upsert(doc("r2", texto=LONG + " dos", caratula="SOSA c/ ACME s/DESPIDO"))
    remote.upsert(doc("shared", texto=LONG + " version remota"))
    remote.record_search("pjn", "5-5|C_7|*|D|2025-10-01|2025-10-01", total=2, fetched=2, split=False, truncated=False)
    remote.close()

    stats = main.merge_from(tmp_path / "vps.db")

    assert stats == {"documents": 3, "searches": 1}
    assert main.count() == 3
    assert main.get("pjn", "r2")["objeto"] == "DESPIDO"            # enrichment recomputed
    assert main.get("pjn", "r2")["status"] == "indexable"          # contract re-applied
    assert main.search_done("pjn", "5-5|C_7|*|D|2025-10-01|2025-10-01")
    main.close()


def test_merge_is_idempotent(tmp_path):
    main = Catalog(tmp_path / "main.db")
    remote = Catalog(tmp_path / "vps.db")
    remote.upsert(doc("r1"))
    remote.close()
    main.merge_from(tmp_path / "vps.db")
    main.merge_from(tmp_path / "vps.db")
    assert main.count() == 1
    main.close()


def test_sala_de_feria_is_recognized(cat):
    cat.upsert(doc("f1", tribunal="CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA FERIA"))
    assert cat.get("pjn", "f1")["sala"] == "FERIA"


# -- accounting: what each search listed and which PDFs failed ------------------------------

def test_listings_are_recorded_once_per_search(cat):
    cat.record_listing("pjn", "5-5|C_1|*|D|2026-08-01|2026-08-04", ["a", "b"])
    cat.record_listing("pjn", "5-5|C_1|*|D|2026-08-01|2026-08-04", ["b", "c"])     # a re-run lists again
    rows = cat.db.execute("SELECT source_id FROM listings ORDER BY source_id").fetchall()
    assert [r[0] for r in rows] == ["a", "b", "c"]


def test_a_failure_counts_attempts_and_is_cleared_by_a_later_success(cat):
    for _ in range(2):
        cat.record_failure("pjn", "x1", url="https://x/1.pdf", key="k", reason="EmptyFileError")
    row = cat.db.execute("SELECT * FROM failures WHERE source_id='x1'").fetchone()
    assert (row["attempts"], row["reason"], row["key"], row["url"]) == (2, "EmptyFileError", "k", "https://x/1.pdf")
    cat.clear_failure("pjn", "x1")
    assert cat.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] == 0
