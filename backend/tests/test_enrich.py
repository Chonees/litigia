"""Enrichment: the fields a litigator reads first, extracted at ingest for $0."""

from pathlib import Path

from scripts.enrich import (
    enrich,
    extract_normas,
    extract_numero,
    extract_objeto,
    extract_resultado,
    extract_votos,
    por_mayoria,
)

FIXTURES = Path(__file__).parent / "fixtures"
GONZALEZ = (FIXTURES / "pjn_cnat_gonzalez_aragon.txt").read_text(encoding="utf-8")   # CNAT IV, SD 115.631
RIVAS = (FIXTURES / "pjn_cnat_disidencia.txt").read_text(encoding="utf-8")           # CNAT, recurso ley 27.348
DESPOSITO = (FIXTURES / "pjn_breve_desposito.txt").read_text(encoding="utf-8")       # desestima el recurso
SITRAMEN = (FIXTURES / "pjn_breve_sitramen.txt").read_text(encoding="utf-8")         # declara abstracta la cuestión


def test_objeto_is_what_follows_s_slash_in_the_caratula():
    assert extract_objeto("GONZALEZ ARAGON, PABLO EZEQUIEL c/ ASOCIART ART S.A. s/ACCIDENTE - LEY ESPECIAL") == "ACCIDENTE - LEY ESPECIAL"
    assert extract_objeto("OLMEDO, FELIX ARIEL c/ GALENO ART S.A. s/RECURSO LEY 27348") == "RECURSO LEY 27348"
    assert extract_objeto("SOSA c/ ACME S.A. s/ despido") == "DESPIDO"
    assert extract_objeto("CPE 000994/2024/2/CA001") == ""


def test_resultado_from_the_resolutive_part():
    assert extract_resultado(GONZALEZ) == "confirma"
    assert extract_resultado(RIVAS) == "confirma"
    assert extract_resultado(DESPOSITO) == "rechaza"
    assert extract_resultado(SITRAMEN) == "abstracto"
    assert extract_resultado("Por ello, el Tribunal RESUELVE: 1) Revocar la sentencia apelada.") == "revoca"
    assert extract_resultado("Por ello, el Tribunal RESUELVE: 1) Modificar parcialmente la sentencia.") == "modifica"
    assert extract_resultado("Texto sin parte resolutiva reconocible.") == ""


def test_resultado_ignores_the_first_instance_decision_described_earlier():
    texto = (
        "II) El Sr. Juez a quo resolvió rechazar la demanda. "
        + "La cuestión exige analizar la prueba. " * 30
        + "Por ello, el Tribunal RESUELVE: 1) Revocar la sentencia apelada y hacer lugar a la demanda."
    )
    assert extract_resultado(texto) == "revoca"


def test_normas_are_normalized():
    assert extract_normas(GONZALEZ) == ["ley 24.557", "ley 27.423"]
    assert "ley 27.348" in extract_normas(RIVAS)
    assert extract_normas(RIVAS).count("ley 27.348") == 1          # "27348" and "27.348" are one law
    assert extract_normas("reclama la multa del art. 80 de la LCT y el art. 245 L.C.T.") == [
        "LCT art. 245", "LCT art. 80",
    ]


def test_numero_de_sentencia():
    assert extract_numero(GONZALEZ) == "SD 115.631"
    assert extract_numero("SENTENCIA INTERLOCUTORIA N° 12.345 AUTOS") == "SI 12.345"
    assert extract_numero(DESPOSITO) == ""


def test_votos_lists_the_judges_in_order():
    assert extract_votos(GONZALEZ) == ["Silvia E. Pinto Varela", "Héctor C. Guisado"]
    assert extract_votos(RIVAS) == ["Graciela L. Craig", "Carlos Pose"]


def test_por_mayoria_only_counts_in_the_resolutive_part():
    assert por_mayoria(GONZALEZ) is False
    assert por_mayoria("… " * 200 + "Por ello, el Tribunal, por mayoría, RESUELVE: 1) Revocar la sentencia.") is True
    assert por_mayoria("La Sala, por mayoría, sostuvo en otro precedente…" + " texto." * 400) is False


def test_enrich_returns_every_field():
    fields = enrich({"caratula": "GONZALEZ ARAGON c/ ASOCIART ART S.A. s/ACCIDENTE - LEY ESPECIAL", "texto": GONZALEZ})
    assert fields == {
        "objeto": "ACCIDENTE - LEY ESPECIAL",
        "resultado": "confirma",
        "normas": ["ley 24.557", "ley 27.423"],
        "numero": "SD 115.631",
        "expediente_texto": "49971/2016",
        "votos": ["Silvia E. Pinto Varela", "Héctor C. Guisado"],
        "por_mayoria": False,
    }


FIRST_INSTANCE_TAIL = (
    "Por todo lo expuesto, citas legales y doctrinarias aplicables, FALLO: 1) Hacer lugar a la demanda "
    "interpuesta por el actor y condenar a SWISS MEDICAL ART S.A. a abonarle la suma de $ 3.500.000. "
    "2) Costas a la demandada. Cópiese, regístrese, notifíquese. Alberto M. González Juez Nacional"
)


def test_resultado_of_a_first_instance_ruling():
    assert extract_resultado("I. Antecedentes... la demandada confirma que... " + FIRST_INSTANCE_TAIL) == "hace lugar"
    assert extract_resultado("Considerando... FALLO: 1) Rechazar la demanda interpuesta. 2) Costas al actor.") == "rechaza"
    assert extract_resultado("...RESUELVO: I.- Condenar a la demandada a pagar.") == "hace lugar"


def test_instancia_from_the_tribunal_name():
    from scripts.enrich import detect_instancia
    assert detect_instancia("CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA IV") == "camara"
    assert detect_instancia("JUZGADO NACIONAL DE 1RA INSTANCIA DEL TRABAJO NRO. 40") == "primera"
    assert detect_instancia("Corte Suprema de Justicia de la Nacion") == "corte"
    assert detect_instancia("") == ""


# -- cases found by the blind extraction of 60 rulings (2026-09-28) ---------------------

def test_numero_of_first_instance_headings():
    assert extract_numero("SENTENCIA NÚMERO: 18867 EXPEDIENTE NÚMERO: 1/2020") == "SD 18867"
    assert extract_numero("SENTENCIA N°: 26849 EXPEDIENTE N°: 2/2021") == "SD 26849"
    assert extract_numero("SENTENCIA Nro.: 7259 EXPTE") == "SD 7259"
    assert extract_numero("SENTENCIA DEFINITIVA NRO.: 15.835 EXPEDIENTE") == "SD 15.835"


def test_numero_ignores_case_numbers_and_panel_codes():
    assert extract_numero("SENTENCIA CNAT NÚMERO: 31748/2021 AUTOS") == ""
    assert extract_numero("SENT.DEF. 2-3-1 EXPTE. Nº: 3.638/2022") == ""


def test_votos_headed_with_manifesto():
    texto = ("el doctor GABRIEL de VEDIA dijo: I. La sentencia... "
             "La doctora BEATRIZ E. FERDMAN manifestó: Que adhiero al voto que antecede.")
    assert extract_votos(texto) == ["Gabriel de Vedia", "Beatriz E. Ferdman"]


def test_resultado_resolutive_verbs_seen_in_real_rulings():
    assert extract_resultado("FALLO: I.-) Haciendo lugar a la demanda interpuesta, a quien condeno a abonar") == "hace lugar"
    assert extract_resultado("el Tribunal RESUELVE: 1) Declarar mal concedido el recurso. 2) Confirmar los honorarios") == "rechaza"
    assert extract_resultado("RESUELVE: 1) Dejar sin efecto la declaración de deserción; 2) Confirmar la resolución") == "revoca"


def test_votos_with_comma_or_without_colon():
    # Real headings from the held-out sample (CNAT Salas I, IX, X, 2026)
    texto = ("El Dr. LEONADO J. AMBESI dijo: I. Vienen los autos... "
             "La Dra. MARÍA CECILIA HOCKL, dijo: En cuanto al tratamiento de los agravios... "
             "El Dr. Victor A. Pesino dijo Por análogos fundamentos, me adhiero al voto que antecede.")
    assert [v.split()[-1].upper() for v in extract_votos(texto)] == ["AMBESI", "HOCKL", "PESINO"]


def test_a_judge_quoted_in_the_reasoning_is_not_a_vote():
    texto = "El Dr. GUISADO dijo: I. Como bien dijo el Dr. Pérez dijo que corresponde confirmar."
    assert [v.split()[-1].upper() for v in extract_votos(texto)] == ["GUISADO"]


def test_expediente_as_written_in_the_ruling():
    from scripts.enrich import extract_expediente_texto
    assert extract_expediente_texto("EXPTE. Nº CNT 46676/2016/CA1 SENTENCIA DEFINITIVA nº 92556") == "46676/2016"
    assert extract_expediente_texto("SENTENCIA DEFINITIVA Nº 8258 AUTOS: “PRIETO” (Expte. N° 3.630/2021) Buenos Aires") == "3630/2021"
    assert extract_expediente_texto("JUZGADO Nº 35 EXPEDIENTE NRO. 19528/18 AUTOS: “OTRERA”") == "19528/18"
    assert extract_expediente_texto("SENTENCIA DEFINITIVA CAUSA N° 49971/2016 SALA IV") == "49971/2016"
    assert extract_expediente_texto("SENTENCIA NÚMERO: 5076 EXPEDIENTE NÚMERO: 33658/2017 AUTOS") == "33658/2017"
    assert extract_expediente_texto("Buenos Aires, 4 de marzo de 2024. VISTOS: el art. 80 de la ley 20.744") == ""


def test_expediente_mismatch_is_flagged():
    from scripts.quality import assess
    base = {"texto": "I.- x " * 400 + "\n\nII.- y\n\nIII.- z", "fecha": "2026-01-01", "caratula": "A c/ B s/DESPIDO",
            "tribunal": "CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA I"}
    assert "expediente_no_coincide" in assess({**base, "expediente": "CNT 046676/2019/CA001",
                                               "expediente_texto": "46676/2016"}).warnings
    assert "expediente_no_coincide" not in assess({**base, "expediente": "CNT 019528/2018",
                                                   "expediente_texto": "19528/18"}).warnings
