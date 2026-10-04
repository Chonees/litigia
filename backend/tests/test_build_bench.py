"""The search benchmark must not leak the answer into the query, and its dev/test split must be stable."""

from spikes.build_bench import leaked_words, leaks, split


def test_party_names_in_the_query_are_a_leak():
    caratula = "GONZALEZ ARAGON, MARIA c/ ASOCIART ART S.A. s/ RECURSO LEY 27348"
    assert leaked_words("Mi clienta reclama a Asociart por una incapacidad psicológica", caratula) == {"ASOCIART"}
    assert leaked_words("Trabajadora con incapacidad psicologica rechazada por la comision medica", caratula) == set()


def test_procedural_words_of_the_caratula_are_not_a_leak():
    # "despido", "recurso", "ley" or "daños" describe the case type, not the parties
    caratula = "PEREZ, JUAN c/ BANCO GALICIA S.A. s/ DESPIDO"
    assert leaked_words("despido de un empleado bancario por pérdida de confianza", caratula) == set()
    caratula = "LOPEZ c/ TRANSPORTES DEL SUR s/ DAÑOS Y PERJUICIOS"
    assert leaked_words("daños y perjuicios por un choque con un colectivo", caratula) == set()


def test_accents_and_case_do_not_hide_a_leak():
    assert leaked_words("demanda contra la firma Peñaflor", "ROLDAN c/ PENAFLOR S.A. s/ DESPIDO") == {"PENAFLOR"}


def test_words_common_across_caratulas_do_not_identify_the_case():
    # "club", "edificio" or "obra social" appear in many carátulas: naming them does not point to one ruling
    caratula = "A., M. c/ Club Atlético River Plate s/ daños y perjuicios"
    query = "espectador herido al ingresar al estadio; responsabilidad del club organizador"
    assert leaked_words(query, caratula) == {"CLUB"}
    assert leaked_words(query, caratula, common={"CLUB", "ATLETICO"}) == set()
    assert leaked_words("demanda contra River Plate", caratula, common={"CLUB"}) == {"RIVER", "PLATE"}


def test_a_norm_number_is_not_a_case_number():
    cita = {"caratula": "SAVOINI c/ PROVINCIA ART SA"}
    assert leaks("¿rige el decreto 669/19 o las resoluciones SSN 1039/2019 y 332/2023? ¿y el DNU 274/2024?", cita, "") == []
    assert leaks("busco el expediente 76722/2017 de la Sala III", cita, "") == ["número de expediente"]


def test_the_split_is_deterministic_and_keeps_both_sets():
    keys = [f"lab-portales-{i}" for i in range(40)]
    first = {k: split(k) for k in keys}
    assert first == {k: split(k) for k in keys}
    assert set(first.values()) == {"dev", "test"}
