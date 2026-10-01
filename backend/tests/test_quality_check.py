"""The cross-checks of spikes/quality_check.py must not flag correct data from other fueros."""

from spikes.quality_check import judges_sign, sala_key, salas_named


def test_sala_numbers_match_whatever_numeral_the_text_uses():
    # seguridad social stores "2"; the heading may say "SALA II" or "SALA 2"
    assert sala_key("2") == sala_key("II") == sala_key("ii")
    assert salas_named("CAMARA FEDERAL DE LA SEGURIDAD SOCIAL - SALA II") == {sala_key("2")}
    assert salas_named("Sala 3 de la Cámara") == {sala_key("III")}


def test_civil_sala_letters_are_recognised_but_not_sala_de_acuerdos():
    assert salas_named("CAMARA CIVIL - SALA C") == {"C"}
    assert salas_named("reunidos en la Sala de Acuerdos") == set()


def test_a_judge_with_a_compound_surname_signs():
    votos = ["Juan Alberto Fantini", "Walter F. Carnota"]
    firmantes = ["JUAN A FANTINI ALBARENQUE", "WALTER FABIAN CARNOTA"]
    assert judges_sign(votos, firmantes)
    assert not judges_sign(["Pedro Gómez"], firmantes)


def test_salas_of_the_tax_court_are_not_the_chambers_own():
    # CNACAF reviews the Tribunal Fiscal: "la Sala E del Tribunal Fiscal de la Nación rechazó el recurso"
    assert salas_named("CAMARA CONTENCIOSO ADMINISTRATIVO FEDERAL - SALA V. Que la Sala “E” del Tribunal Fiscal "
                       "de la Nación rechazó el recurso") == {sala_key("V")}


def test_the_stored_number_in_the_heading_is_never_a_contradiction():
    from spikes.quality_check import expediente_contradicted
    head = ("CAMARA CONTENCIOSO ADMINISTRATIVO FEDERAL - SALA IV – CAF 17946/2025/CA3 “DNM c/ FERNANDEZ - "
            "EXPTE 2151497/06 s/MEDIDAS DE RETENCION”")
    assert not expediente_contradicted("CAF 017946/2025/CA003", head)
    assert expediente_contradicted("CAF 005142/2025/CA001", "Causa Nº 18.269/2024/CA1 Briones Marrero")
