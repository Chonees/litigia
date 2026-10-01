"""The data contract: what a fallo must have to be useful for LITIGIA search."""

from pathlib import Path

from scripts.quality import (
    assess,
    clean_pjn_text,
    detect_fuero,
    detect_tipo,
    extract_firmantes,
    split_paragraphs,
    text_hash,
)

PAGE_HEADER = "#34510739#284957179#20210331152026453\nPoder Judicial de la Nación\nCAMARA CIVIL - SALA E\n"
SIGNATURE = (
    "Fecha de firma: 31/03/2021\n"
    "Alta en sistema: 06/04/2021\n"
    "Firmado por: FERNANDO MARTIN RACIMO, JUEZ DE CAMARA\n"
    "Firmado por: CLAUDIO RAMOS FEIJOO, JUEZ DE CAMARA\n\n"
)

RAW = (
    PAGE_HEADER
    + "Buenos Aires, 31 de marzo de 2021.-\n"
    "Y VISTOS:CONSIDERANDO:\n"
    "I.-Contra la resolución dictada en la instancia de grado en \n"
    "fecha 2 de diciembre de 2020 se alzan la parte actora y la citada en \n"
    "garantía por las quejas que vierten en sendas presentaciones.\n"
    "En dicho pronunciamiento la Sra. juez de la anterior \n"
    "instancia señaló que el allanamiento debía diferirse.\n"
    + SIGNATURE
    + PAGE_HEADER
    + "II.-Por las razones expuestas, SE RESUELVE: Revocar la \n"
    "sentencia interlocutoria. Notifíquese y devuélvase.-\n"
    + SIGNATURE
)


def good_doc(**overrides) -> dict:
    body = "\n\n".join(
        f"{n}.- La cuestión traída a conocimiento del Tribunal exige analizar el art. 80 de la "
        "Ley de Contrato de Trabajo y la jurisprudencia aplicable al caso concreto. " * 3
        for n in ("I", "II", "III", "IV")
    )
    doc = {
        "texto": body,
        "fecha": "2021-03-31",
        "tribunal": "CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA I",
        "caratula": "OLMEDO, FELIX ARIEL c/ GALENO ART S.A. s/RECURSO LEY 27348",
        "expediente": "CNT 044625/2024/CA001",
    }
    doc.update(overrides)
    return doc


# -- cleaning ---------------------------------------------------------------

def test_clean_removes_page_hashes_signatures_and_repeated_headers():
    clean = clean_pjn_text(RAW)
    assert "#34510739#" not in clean
    assert "Fecha de firma" not in clean
    assert "Firmado por" not in clean
    assert "Poder Judicial de la Nación" not in clean
    assert "CAMARA CIVIL - SALA E" not in clean
    assert "Revocar la sentencia interlocutoria" in clean


def test_clean_joins_lines_broken_by_the_pdf():
    clean = clean_pjn_text(RAW)
    assert "se alzan la parte actora y la citada en garantía" in clean


def test_split_paragraphs_keeps_numbered_sections_apart():
    paragraphs = split_paragraphs(clean_pjn_text(RAW))
    assert any(p.startswith("I.-Contra la resolución") for p in paragraphs)
    assert any(p.startswith("II.-Por las razones expuestas") for p in paragraphs)
    assert all("\n" not in p for p in paragraphs)


def test_extract_firmantes_and_signature_date():
    firmantes, fecha = extract_firmantes(RAW)
    assert firmantes == ["FERNANDO MARTIN RACIMO", "CLAUDIO RAMOS FEIJOO"]
    assert fecha == "2021-03-31"


def test_firmantes_are_judges_not_clerks():
    raw = SIGNATURE + "Firmado por: ANA PEREZ, SECRETARIA DE CAMARA\nFirmado por: LUIS GOMEZ, PROSECRETARIO DE CAMARA\n"
    raw += "Firmado por: MARIA SOSA, JUEZA DE CÁMARA\nFirmado por: EVA DIAZ, PRESIDENTA DE CAMARA\n"
    firmantes, _ = extract_firmantes(raw)
    assert firmantes == ["FERNANDO MARTIN RACIMO", "CLAUDIO RAMOS FEIJOO", "MARIA SOSA", "EVA DIAZ"]


# -- real PDF text (downloaded from PJN, CPE 994/2024, Sala A) ------------------

REAL = (Path(__file__).parent / "fixtures" / "pjn_sentencia_raw.txt").read_text(encoding="utf-8")


def test_real_ruling_is_cleaned_into_paragraphs():
    clean = clean_pjn_text(REAL)
    paragraphs = split_paragraphs(clean)
    assert len(paragraphs) > 50
    assert "Firmado por" not in clean
    assert "Fecha de firma" not in clean
    assert any(p == "VISTOS:" for p in paragraphs)


def test_real_ruling_meets_the_contract():
    firmantes, fecha = extract_firmantes(REAL)
    assert firmantes == ["CAROLINA ROBIGLIO", "ROBERTO ENRIQUE HORNOS"]
    result = assess({
        "texto": clean_pjn_text(REAL),
        "fecha": fecha,
        "tribunal": "CAMARA PENAL ECONOMICO - SALA A",
        "caratula": "Legajo Nº 2 - NN: R. A, H. R. s/LEGAJO DE APELACION",
        "expediente": "CPE 000994/2024/2/CA001",
    })
    assert result.status == "indexable", result.reasons


# -- metadata ---------------------------------------------------------------

def test_detect_fuero_from_tribunal_name():
    assert detect_fuero("CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA I") == "laboral"
    assert detect_fuero("CAMARA CIVIL - SALA E") == "civil"
    assert detect_fuero("CÁMARA NACIONAL DE APELACIONES EN LO COMERCIAL - SALA D") == "comercial"
    assert detect_fuero("CAMARA PENAL ECONOMICO - SALA A") == "penal economico"
    assert detect_fuero("CÁMARA FEDERAL DE APELACIONES DE LA SEGURIDAD SOCIAL - SALA 2") == "seguridad social"
    assert detect_fuero("CÁMARA NACIONAL DE APELACIONES EN LO CIVIL Y COMERCIAL FEDERAL") == "civil y comercial federal"
    assert detect_fuero("CAMARA FEDERAL DE PARANÁ") == "federal"
    assert detect_fuero("") == ""


def test_text_hash_ignores_whitespace_and_case():
    assert text_hash("Hola   Mundo\n") == text_hash("hola mundo")


# -- the contract -----------------------------------------------------------

def test_complete_ruling_is_indexable():
    result = assess(good_doc())
    assert result.status == "indexable", result.reasons
    assert result.reasons == []


def test_short_text_is_rejected():
    result = assess(good_doc(texto="Téngase presente. Notifíquese."))
    assert result.status == "rejected"
    assert "texto_corto" in result.reasons


FIXTURES = Path(__file__).parent / "fixtures"


def test_brief_ruling_with_a_real_criterion_is_kept_with_a_warning():
    # CNAT Sala X, 06/03/2024: two paragraphs, but it fixes the 15-day term to appeal
    # the Comisión Médica Central (acta 2669/2018). A lawyer wants this one.
    texto = (FIXTURES / "pjn_breve_desposito.txt").read_text(encoding="utf-8")
    result = assess(good_doc(texto=texto))
    assert result.status == "indexable", result.reasons
    assert "breve" in result.warnings


def test_brief_ruling_that_only_declares_the_case_moot_is_rejected():
    # CNAT Sala X, 07/03/2024: declares the question abstract and orders the archive.
    texto = (FIXTURES / "pjn_breve_sitramen.txt").read_text(encoding="utf-8")
    result = assess(good_doc(texto=texto))
    assert result.status == "rejected"
    assert "resolucion_formal" in result.reasons


def test_detect_tipo_from_the_ruling_itself():
    assert detect_tipo("SENT.INT. 3 - 2  EXPTE. Nº: 3.638/2022/CA1") == "I"
    assert detect_tipo("SENT. INT. 3-2 EXPTE. Nº: 52.323/2023") == "I"
    assert detect_tipo("SENTENCIA INTERLOCUTORIA N° 1234") == "I"
    assert detect_tipo("SENTENCIA DEFINITIVA N° 115.631 CAUSA N° 49971/2016") == "D"
    assert detect_tipo("Buenos Aires, 4 de marzo de 2024.") == ""


def test_site_label_that_contradicts_the_text_is_flagged():
    texto = (FIXTURES / "pjn_breve_desposito.txt").read_text(encoding="utf-8")
    result = assess(good_doc(texto=texto, tipo_fallo="D"))
    assert "tipo_no_coincide" in result.warnings


def test_short_formal_resolution_is_rejected():
    texto = "Considerando: Que el recurso extraordinario es inadmisible (art. 280 del Código Procesal). " * 8
    result = assess(good_doc(texto=texto))
    assert result.status == "rejected"
    assert "resolucion_formal" in result.reasons


def test_long_ruling_that_mentions_art_280_is_kept():
    doc = good_doc()
    doc["texto"] = "\n\n".join([doc["texto"]] * 3) + "\n\nSe cita el art. 280 del Código Procesal a modo de referencia."
    assert assess(doc).status == "indexable"


def test_missing_metadata_is_pending_not_rejected():
    result = assess(good_doc(fecha="", tribunal=""))
    assert result.status == "pending"
    assert set(result.reasons) >= {"sin_fecha", "sin_tribunal"}


def test_scanned_pdf_without_text_needs_ocr():
    result = assess(good_doc(texto="· ¬ ¦ ° " * 800))
    assert result.status == "pending"
    assert "necesita_ocr" in result.reasons


def test_corte_suprema_has_no_salas():
    result = assess(good_doc(tribunal="Corte Suprema de Justicia de la Nacion"))
    assert "sin_sala" not in result.warnings


def test_missing_sala_is_only_a_warning():
    result = assess(good_doc(tribunal="CAMARA FEDERAL DE PARANÁ"))
    assert result.status == "indexable"
    assert "sin_sala" in result.warnings


BRIEF_CSJN_PROCEDURAL = {
    "honorarios": (
        "Autos y Vistos: En atención a los trabajos realizados en la contestación del recurso "
        "extraordinario, el motivo, la extensión y la calidad jurídica de la labor desarrollada y lo "
        "dispuesto por los arts. 16 y 19 de la ley 27.423, se regulan los honorarios de la doctora "
        "Silvina Sáenz en la suma de un millón cincuenta mil pesos ($ 1.050.200), que representan "
        "20 UMA. Notifíquese y devuélvase. "
    ),
    "mejor_proveer": (
        "Autos y Vistos: Como medida para mejor proveer, atento el tiempo transcurrido desde la "
        "última presentación realizada por el señor Gobernador de la provincia de Salta ante esta "
        "Corte, requiérasele que informe sobre el estado actual del trámite del proyecto de ley "
        "destinado a obtener la expropiación de una fracción del inmueble. Notifíquese. "
    ),
    "queja_extemporanea": (
        "Vistos los autos: Recurso de hecho deducido por la demandada para decidir sobre su "
        "procedencia. Considerando: Que el recurso de queja ha sido interpuesto extemporáneamente "
        "(arts. 282 y 285 del Código Procesal Civil y Comercial de la Nación). Por ello, se lo "
        "desestima. Notifíquese y archívese. "
    ),
    "deposito_286": (
        "Autos y Vistos: Intímase a la parte recurrente para que, dentro del quinto día de "
        "notificada, efectúe el depósito previsto en el art. 286 del Código Procesal Civil y "
        "Comercial de la Nación, bajo apercibimiento de tener por no presentado el recurso. "
    ),
}


def test_brief_procedural_resolutions_are_rejected():
    for name, texto in BRIEF_CSJN_PROCEDURAL.items():
        texto = "\n\n".join([texto] * 4)[:1400]
        result = assess(good_doc(texto=texto))
        assert result.status == "rejected", name
        assert "resolucion_formal" in result.reasons, name


def test_procedural_patterns_do_not_reject_long_rulings():
    doc = good_doc()
    doc["texto"] = "\n\n".join([doc["texto"]] * 4) + "\n\nSe regulan los honorarios de los profesionales intervinientes."
    assert assess(doc).status == "indexable"


def test_page_numbers_are_not_paragraphs():
    from scripts.quality import strip_noise_paragraphs
    texto = "I) Primer párrafo con contenido jurídico relevante.\n\n2\n\n:\n\n- 3 -\n\nII) Segundo párrafo con contenido."
    assert split_paragraphs(strip_noise_paragraphs(texto)) == [
        "I) Primer párrafo con contenido jurídico relevante.",
        "II) Segundo párrafo con contenido.",
    ]


def test_first_instance_rulings_have_no_sala_to_miss():
    result = assess(good_doc(tribunal="JUZGADO NACIONAL DE 1RA INSTANCIA DEL TRABAJO NRO. 40"))
    assert "sin_sala" not in result.warnings


def test_numeric_tables_are_not_noise():
    # A liquidation table extracted from a PDF is only numbers and punctuation, but it is content:
    # amounts, dates and percentages a labor lawyer reads. Only page-number-sized fragments are noise.
    from scripts.quality import strip_noise_paragraphs
    # Real rows from an IBM calculation (CNAT, Galeno ART, Ley 27.348): salary, month, coefficient, total.
    row = "1.255.660,91 07/2023 (1,00000) 309.398,42"
    total = "11.888.158,60"
    texto = f"I) Ingreso base mensual:\n\n{row}\n\n12\n\n{total}\n\nII) Costas a la demandada."
    assert split_paragraphs(strip_noise_paragraphs(texto)) == [
        "I) Ingreso base mensual:", row, total, "II) Costas a la demandada.",
    ]


# CFSS Sala 2, retiro por invalidez (2026-03/04): a short ruling on the merits that only NARRATES an earlier
# "medida para mejor proveer". It was rejected as formal; the phrase only counts in the resolutive part.
RETIRO_INVALIDEZ = "\n\n".join([
    "VISTO: Las presentes actuaciones llegan a conocimiento del Tribunal en virtud del recurso interpuesto por el "
    "actor contra la resolución de la Comisión Médica Central que le denegó el retiro por invalidez.",
    "La Comisión Médica Central determinó que el peticionante presenta un porcentaje de incapacidad inferior al "
    "exigido por el artículo 48, inciso a) de la ley 24.241, por lo cual denegó el beneficio pretendido.",
    "En efecto, conforme surge de autos, el Tribunal dispuso como medida para mejor proveer la remisión de las "
    "actuaciones al Cuerpo Médico Forense. Del informe médico producido se desprende que presenta una incapacidad "
    "física que supera el 66% de la total obrera, extremo que habilita el beneficio.",
    "Por ello, el Tribunal RESUELVE: 1º) Revocar la resolución de la Comisión Médica Central. 2º) Ordenar a la "
    "ANSeS que otorgue al actor el retiro por invalidez. 3º) Remitir las presentes actuaciones al organismo de "
    "origen a sus efectos. Regístrese, publíquese, notifíquese y oportunamente devuélvase.",
] * 2)


def test_a_narrated_medida_para_mejor_proveer_does_not_make_a_ruling_formal():
    assert assess(good_doc(texto=RETIRO_INVALIDEZ)).status != "rejected"


def test_a_ruling_that_orders_a_medida_para_mejor_proveer_is_formal():
    texto = "\n\n".join(["VISTO: Las actuaciones llegan al Tribunal por el recurso del actor contra la Comisión Médica."] * 8
                        + ["Por ello, el Tribunal RESUELVE: Disponer como medida para mejor proveer la remisión de las "
                           "actuaciones al Cuerpo Médico Forense. Notifíquese."])
    assert assess(good_doc(texto=texto)).status == "rejected"


def test_tax_enforcement_courts_belong_to_the_contencioso_fuero():
    # they hang from the Cámara Contencioso Administrativo Federal (C_2); 127 rulings in 2025-2026
    assert detect_fuero("JUZGADO FEDERAL DE EJECUCIONES FISCALES TRIBUTARIAS Nº 5 - SECRETARIA Nº 18") == \
        "contencioso administrativo federal"


def test_fee_only_rulings_are_rejected_whatever_their_length():
    # CNACAF publishes as "definitivas" rulings that only decide fee appeals; they open with this template
    texto = "\n\n".join(["AUTOS Y VISTOS: Que, a fin de tratar el recurso interpuesto, cabe señalar que, mediante la "
                         "regulación de honorarios se busca compensar de modo adecuado la tarea desplegada por los "
                         "profesionales, conforme la ley 27.423."] + ["Se fijan los honorarios de la dirección letrada. " * 20] * 8)
    result = assess(good_doc(texto=texto))
    assert len(texto) > 4000
    assert result.status == "rejected"
    assert "solo_honorarios" in result.reasons


def test_a_ruling_on_the_merits_that_later_regulates_fees_is_kept():
    doc = good_doc()
    doc["texto"] += "\n\nMediante la regulación de honorarios se busca compensar la labor profesional."   # at the end, not the opening
    assert assess(doc).status == "indexable"
