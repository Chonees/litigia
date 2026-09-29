from pathlib import Path

from scripts.import_legacy import from_csjn, from_pjn
from scripts.quality import detect_fuero

REAL = (Path(__file__).parent / "fixtures" / "pjn_sentencia_raw.txt").read_text(encoding="utf-8")


def test_legacy_pjn_row_is_rebuilt_from_its_own_text():
    row = {
        "source": "pjn_tribunales",
        "source_id": "1437814a-79c8-4e12-8eda-2609c5b36e2e",
        "texto": REAL,
        "caratula": "FSM 150590/2018/CA001",   # old parser bug: an expediente, maybe the neighbour's
        "tribunal": "",
        "fecha": "",
        "jurisdiccion": "Ciudad de Buenos Aires",
    }
    doc = from_pjn(row)
    assert doc["source"] == "pjn"
    assert doc["source_id"] == "1437814a-79c8-4e12-8eda-2609c5b36e2e"
    assert doc["tribunal"] == ""   # this PDF names the court only in signatures ("JUEZ DE CAMARA")
    assert doc["fecha"] == "2024-12-31"
    assert doc["firmantes"] == ["CAROLINA ROBIGLIO", "ROBERTO ENRIQUE HORNOS"]
    assert doc["caratula"] == "" and doc["expediente"] == ""
    assert "Firmado por" not in doc["texto"]


def test_legacy_pjn_takes_tribunal_from_the_page_header():
    raw = "#1#2#3\nPoder Judicial de la Nación\nCAMARA CIVIL - SALA E\n103480/2019\n" + REAL
    assert from_pjn({"source_id": "x", "texto": raw})["tribunal"] == "CAMARA CIVIL - SALA E"


def test_legacy_csjn_row_keeps_its_metadata():
    row = {
        "source": "csjn",
        "source_id": "8191261",
        "texto": "CIV 107043/2008/2/RH1\nPosch, Rosa Isabel c/ Vidal\nVistos los autos: \n“Recurso de hecho”.",
        "caratula": "Recurso Queja N° 2 - POSCH ROSA ISABEL c/ VIDAL FABIAN JORGE",
        "tribunal": "Corte Suprema de Justicia de la Nacion",
        "fecha": "11/11/2025",
        "jurisdiccion": "Nacional",
    }
    doc = from_csjn(row)
    assert doc["source"] == "csjn"
    assert doc["fecha"] == "2025-11-11"
    assert doc["caratula"].startswith("Recurso Queja")
    assert doc["expediente"] == "CIV 107043/2008/2/RH1"


def test_corte_suprema_has_its_own_fuero():
    assert detect_fuero("Corte Suprema de Justicia de la Nacion") == "corte suprema"
