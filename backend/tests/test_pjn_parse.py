from datetime import date, timedelta
from pathlib import Path

from scripts.scrapers.pjn_parse import CAP, crawl, parse_oficinas, parse_results, parse_token, parse_total

FIXTURE = (Path(__file__).parent / "fixtures" / "pjn_results_page.html").read_text(
    encoding="utf-8", errors="replace"
)


# -- results page parsing -----------------------------------------------------

def test_parses_every_result_on_the_page():
    assert len(parse_results(FIXTURE)) == 20


def test_each_result_keeps_its_own_metadata():
    first = parse_results(FIXTURE)[0]
    assert first["tribunal"] == "CAMARA PENAL ECONOMICO - SALA A"
    assert first["expediente"] == "CPE 000994/2024/2/CA001"
    assert first["caratula"].startswith("Legajo Nº 2")
    assert first["fecha"] == "2024-12-31"
    assert first["uuid"] == "1437814a-79c8-4e12-8eda-2609c5b36e2e"
    assert first["pdf_url"].endswith("sentencia-SGU-1437814a-79c8-4e12-8eda-2609c5b36e2e.pdf?fecha=31/12/2024")


def test_no_result_mixes_metadata_from_a_neighbour():
    for r in parse_results(FIXTURE):
        assert r["uuid"] in r["pdf_url"]
        assert r["tribunal"] and r["fecha"] and r["caratula"]


def test_falls_back_to_visible_labels_without_viewer_link():
    page = FIXTURE.replace("info=", "nfo=")
    first = parse_results(page)[0]
    assert first["tribunal"] == "CAMARA PENAL ECONOMICO - SALA A"
    assert first["expediente"] == "CPE 000994/2024/2/CA001"
    assert first["fecha"] == "2024-12-31"


def test_parse_token_for_the_next_page():
    assert parse_token(FIXTURE) == "da78ae3872a8806a164f78000ba6a9f4b61d0276bcd63c92b94f41f2c6e5b731"
    assert parse_token("<html>sin token</html>") == ""


def test_parse_oficinas_lists_salas_without_the_empty_option():
    html = (
        '<option value="">Indistinto</option>'
        '<option value="T_7_TS1" >Cámara Nacional de Apelaciones Del Trabajo - Sala I</option>'
        '<option value="T_7_TS2" >Cámara Nacional de Apelaciones Del Trabajo - Sala II</option>'
    )
    assert parse_oficinas(html) == [
        ("T_7_TS1", "Cámara Nacional de Apelaciones Del Trabajo - Sala I"),
        ("T_7_TS2", "Cámara Nacional de Apelaciones Del Trabajo - Sala II"),
    ]


def test_site_cap_is_five_pages_of_twenty():
    # Measured live on 2026-09-27: page 5 comes back empty with total 1,319.
    assert CAP == 100


def test_parse_total():
    assert parse_total(FIXTURE) == 192565
    assert parse_total("Su búsqueda arrojó 1.234 resultados") == 1234
    assert parse_total("La búsqueda no ha arrojado resultados") == 0


# -- adaptive crawl -------------------------------------------------------------

def fake_site(per_day: dict[date, int], cap: int = CAP):
    """A site with `per_day[d]` rulings each day that returns at most `cap` per search."""
    calls = []

    def search(start: date, end: date):
        calls.append((start, end))
        docs = [
            f"{d}-{i}"
            for d, n in per_day.items() if start <= d <= end
            for i in range(n)
        ]
        return len(docs), docs[:cap]

    return search, calls


def collected(records) -> set[str]:
    return {doc for r in records if not r.split for doc in r.results}


def test_range_under_the_cap_is_a_single_search():
    days = {date(2024, 3, d): 1 for d in range(1, 31)}
    search, calls = fake_site(days)
    records = list(crawl(search, date(2024, 3, 1), date(2024, 3, 31)))
    assert len(calls) == 1
    assert len(collected(records)) == 30
    assert not any(r.truncated for r in records)


def test_range_over_the_cap_is_split_until_everything_fits():
    days = {date(2024, 3, 1) + timedelta(days=i): 12 for i in range(31)}  # 372 rulings, over the cap
    search, _ = fake_site(days)
    records = list(crawl(search, date(2024, 3, 1), date(2024, 3, 31)))
    assert len(collected(records)) == 372
    assert not any(r.truncated for r in records)


def test_single_day_over_the_cap_is_marked_truncated():
    search, _ = fake_site({date(2024, 3, 5): CAP + 15})
    records = list(crawl(search, date(2024, 3, 5), date(2024, 3, 5)))
    assert records[-1].truncated
    assert records[-1].total == CAP + 15
    assert len(collected(records)) == CAP


def test_split_records_report_the_site_total():
    days = {date(2024, 3, 1) + timedelta(days=i): 12 for i in range(31)}
    search, _ = fake_site(days)
    records = list(crawl(search, date(2024, 3, 1), date(2024, 3, 31)))
    assert records[0].split and records[0].total == 372


def test_skip_avoids_searching_ranges_already_done():
    days = {date(2024, 3, 1) + timedelta(days=i): 12 for i in range(31)}
    search, calls = fake_site(days)
    done = set()
    for r in crawl(search, date(2024, 3, 1), date(2024, 3, 31)):
        if not r.split:
            done.add((r.start, r.end))

    search2, calls2 = fake_site(days)
    list(crawl(search2, date(2024, 3, 1), date(2024, 3, 31), skip=lambda s, e: (s, e) in done))
    assert len(calls2) < len(calls)
