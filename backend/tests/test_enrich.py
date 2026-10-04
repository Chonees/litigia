"""Enrichment: the fields a litigator reads first, extracted at ingest for $0.

Resolutive snippets are prefixed with PAD (reasoning): a real ruling resolves at its end.
"""

from pathlib import Path

from scripts.enrich import (
    enrich,
    extract_expediente_texto,
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
    assert extract_resultado(PAD + "Por ello, el Tribunal RESUELVE: 1) Revocar la sentencia apelada.") == "revoca"
    assert extract_resultado(PAD + "Por ello, el Tribunal RESUELVE: 1) Modificar parcialmente la sentencia.") == "modifica"
    assert extract_resultado("Texto sin parte resolutiva reconocible.") == ""


def test_resultado_ignores_the_first_instance_decision_described_earlier():
    texto = (
        "II) El Sr. Juez a quo resolvió rechazar la demanda. "
        + "La cuestión exige analizar la prueba. " * 30
        + "Por ello, el Tribunal RESUELVE: 1) Revocar la sentencia apelada y hacer lugar a la demanda."
    )
    assert extract_resultado(texto) == "revoca"


def test_normas_are_normalized():
    # It also cites the procedural code: "art. 477 CPCCN", "art. 386 y 477 CPCC", "art. 68 2da parte CPCC"
    assert extract_normas(GONZALEZ) == ["CPCCN art. 386", "CPCCN art. 477", "CPCCN art. 68", "ley 24.557", "ley 27.423"]
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
        "normas": ["CPCCN art. 386", "CPCCN art. 477", "CPCCN art. 68", "ley 24.557", "ley 27.423"],
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
    assert extract_resultado(PAD + "I. Antecedentes... la demandada confirma que... " + FIRST_INSTANCE_TAIL) == "hace lugar"
    assert extract_resultado(PAD + "Considerando... FALLO: 1) Rechazar la demanda interpuesta. 2) Costas al actor.") == "rechaza"
    assert extract_resultado(PAD + "...RESUELVO: I.- Condenar a la demandada a pagar.") == "hace lugar"


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
    assert extract_resultado(PAD + "FALLO: I.-) Haciendo lugar a la demanda interpuesta, a quien condeno a abonar") == "hace lugar"
    assert extract_resultado(PAD + "el Tribunal RESUELVE: 1) Declarar mal concedido el recurso. 2) Confirmar los honorarios") == "rechaza"
    assert extract_resultado(PAD + "RESUELVE: 1) Dejar sin efecto la declaración de deserción; 2) Confirmar la resolución") == "revoca"


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


# -- Cámara Nacional Civil and its juzgados (pilot 2026-08/09) ------------------------------

PAD = "Fundamentos del voto y análisis de los agravios de las partes. " * 20


def test_civil_resolutive_opens_with_decide():
    t = PAD + ("Por las razones expuestas y conclusiones establecidas en el Acuerdo transcripto precedentemente, por unanimidad "
               "de votos el Tribunal decide: 1) Confirmar la sentencia en todo lo que ha sido motivo de recurso y agravio; "
               "2) Imponer las costas de ambas instancias al Sr. Pico (art. 68, CPCC).")
    assert extract_resultado(t) == "confirma"


def test_civil_resolutive_verbs_with_accents_and_subjunctive():
    t = PAD + ("Y VISTOS: En virtud a lo que resulta de la votación de que da cuenta el acuerdo que antecede, se resuelve: "
               "1) Fijar que se aplique el interés tal como lo explicitado en el considerando VII; 2) Se la confirme en todo lo demás.")
    assert extract_resultado(t) == "confirma"
    assert extract_resultado(PAD + "SE RESUELVE: 1) Modifícase la sentencia apelada en cuanto al daño moral.") == "modifica"
    assert extract_resultado(PAD + "SE RESUELVE: I. Revócase la sentencia de fs. 120.") == "revoca"


def test_civil_first_instance_fallo_decido_and_gerunds():
    assert extract_resultado(PAD + "Por las consideraciones expuestas, Fallo: 1) Haciendo lugar a la demanda.") == "hace lugar"
    assert extract_resultado(PAD + "Por ello, DECIDO: 1) Rechazando la demanda interpuesta, con costas.") == "rechaza"
    assert extract_resultado(PAD + "Por todo lo expuesto, RESUELVO: I) Admitiendo parcialmente la demanda y "
                                   "condenando a la demandada a pagar la suma de $31.800.000.") == "hace lugar"


def test_a_ruling_that_merely_mentions_the_word_fallo_is_not_resolutive():
    assert extract_resultado(PAD + "Como surge del fallo: confirmar la condena no es posible aquí.") == ""


def test_civil_votes_with_judge_titles():
    t = ("A la cuestión planteada el Juez de Cámara Doctor Carranza Casares dijo: I.- La sentencia hizo lugar a la demanda. "
         "El Juez de Cámara Doctor Polo Olivera dijo: Adhiero. "
         "deliberación y voto el orden de sorteo a estudio, la señora juez Doctora Lucila Inés Córdoba dijo: I- A- Vienen los autos")
    assert extract_votos(t) == ["Carranza Casares", "Polo Olivera", "Lucila Inés Córdoba"]


def test_normas_include_civil_and_procedural_code_articles():
    t = ("conforme el art. 1746 del Código Civil y Comercial de la Nación y el art. 1741 del CCyCN; "
         "costas por el art. 68 del Código Procesal; art. 165 del CPCCN; ley 24.449.")
    assert extract_normas(t) == ["CCyC art. 1741", "CCyC art. 1746", "CPCCN art. 165", "CPCCN art. 68", "ley 24.449"]


# -- Cámara Federal de la Seguridad Social ---------------------------------------------------

CFSS_TAIL = (
    "Por ello el Tribunal, por mayoría RESUELVE: 1.- Revocar la sentencia en cuanto a la actualización de la PBU. "
    "2.- Ordenar el reajuste conforme lo expuesto. 3.- Confirmar la sentencia recurrida en lo demás que decide y ha "
    "sido materia de agravios. 4.- Costas por su orden en la Alzada en atención a la forma que se resuelve, arts. 68 "
    "segunda parte del C.P.C.C.N. y 36 de la ley 27.423. Protocolícese, notifíquese y, oportunamente, remítase."
)


def test_la_forma_que_se_resuelve_in_the_costas_is_not_the_resolutive_part():
    assert extract_resultado(PAD + CFSS_TAIL) == "revoca"
    assert por_mayoria(PAD + CFSS_TAIL)


def test_a_marker_in_the_reasoning_does_not_open_the_resolutive_part():
    # Juzgado Civil 95: "corresponde resolver" early in the text, no resolutive formula at the end
    t = "Corresponde resolver el mismo conforme las pruebas, lo que confirma la versión del actor. " + PAD * 3
    assert extract_resultado(t) == ""


def test_comercial_resolves_with_acuerdan():
    t = PAD + ("Así voto. Los Dres. Eduardo R. Machin y Ernesto Lucchelli adhieren al voto que antecede. "
               "Concluida la deliberación los señores Jueces de Cámara acuerdan: I. Confirmar la sentencia de primera "
               "instancia, con costas de Alzada a cargo de Encatesa S.A. II. Diferir la fijación de los honorarios.")
    assert extract_resultado(t) == "confirma"


def test_civil_first_instance_whose_pdf_lost_the_word_fallo():
    assert extract_resultado(PAD + "Por todo lo expuesto, : 1) Haciendo lugar a la demanda.") == "hace lugar"
    assert extract_resultado(PAD + "disposiciones legales, doctrina y jurisprudencia citadas, : I) Rechazar la demanda.") == "rechaza"


def test_civil_first_instance_that_opens_with_the_verb():
    assert extract_resultado(PAD + "Por ello y normas legales citadas, Rechazando la demanda intentada por Pérez.") == "rechaza"
    assert extract_resultado(PAD + "juzgando, en definitiva, Haciendo lugar a la demanda promovida por López.") == "hace lugar"


def test_hacer_parcialmente_lugar():
    t = PAD + "Por ello, FALLO: 1) Hacer parcialmente lugar a la demanda interpuesta por la parte actora."
    assert extract_resultado(t) == "hace lugar"


def test_an_adhesion_does_not_glue_two_judges_into_one_name():
    # CNAT Sala VI, "Benítez c/ Experta ART" (2024-03-25): the adhesion names the first judge, then the third votes
    t = ("LA DOCTORA GRACIELA L. CRAIG DIJO: I. La parte demandada se agravia. "
         "EL DOCTOR CARLOS POSE DIJO: En materia de incapacidad psíquica, debo disentir. "
         "Adhiero al voto de la Dra. Graciela L. Craig. LA Doctora Gabriela Vazquez dijo: Adhiero al voto de la Dra. Craig.")
    assert extract_votos(t) == ["Graciela L. Craig", "Carlos Pose", "Gabriela Vazquez"]


# -- seguridad social, full year (2026-09-30) ------------------------------------------------

def test_first_instance_decides_in_first_person():
    assert extract_resultado(PAD + "Por ello, FALLO: 1) Hago lugar a la demanda y ordeno a la ANSeS reajustar.") == "hace lugar"
    assert extract_resultado(PAD + "Por ello, FALLO: 1) Hago parcialmente lugar a la demanda.") == "hace lugar"
    assert extract_resultado(PAD + "Por ello, RESUELVO: 1) Rechazo la demanda interpuesta. 2) Costas por su orden.") == "rechaza"
    assert extract_resultado(PAD + "Por ello, FALLO: 1) Admito parcialmente la demanda.") == "hace lugar"


def test_rejecting_a_defense_is_not_rejecting_the_claim():
    t = PAD + "Por ello, FALLO: 1) Rechazo la defensa de prescripción. 2) Hago lugar a la demanda."
    assert extract_resultado(t) == "hace lugar"


def test_enclitic_verbs():
    assert extract_resultado(PAD + "el Tribunal RESUELVE: 1) Diferir la regulación de honorarios; 2) Confirmarla en lo demás.") == "confirma"


def test_the_first_item_the_pdf_printed_before_the_marker_is_not_lost():
    # CFSS: the PDF text puts "1) Revocar la sentencia" before "…el Tribunal RESUELVE:", which then continues mid-sentence
    t = PAD + ("1) Revocar la sentencia En virtud de lo expuesto, el Tribunal RESUELVE: apelada en lo que respecta al "
               "plazo de cumplimiento; 2) Diferir la regulación de honorarios; 3) Confirmarla en lo demás que decide.")
    assert extract_resultado(t) == "revoca"


# -- Cámara Contencioso Administrativo Federal, full year (2026-09-30) ------------------------

def test_rejecting_the_appeal_and_confirming_is_confirma():
    t = PAD + ("Por ello, SE RESUELVE: 1) Rechazar el recurso de apelación interpuesto por el Dr. Barragán y, en "
               "consecuencia, confirmar el pronunciamiento apelado. 2) Costas por su orden.")
    assert extract_resultado(t) == "confirma"


def test_decision_stated_before_asi_se_resuelve():
    t = PAD + "Por lo expuesto, corresponde confirmar la sentencia apelada, con costas. Así se resuelve. Regístrese, notifíquese y devuélvase."
    assert extract_resultado(t) == "confirma"


def test_ruling_without_any_resolutive_formula():
    t = "Y VISTOS: los autos. CONSIDERANDO: " + PAD + "Por ello, se revoca la resolución apelada, con costas. Regístrese, notifíquese."
    assert extract_resultado(t) == "revoca"


def test_a_closing_note_with_resolver_does_not_restart_the_resolutive_part():
    t = PAD + ("SE RESUELVE: Confirmar la sentencia apelada. Regístrese y notifíquese. Se deja constancia de que el "
               "Tribunal se encuentra en condiciones de resolver conforme el art. 109 del RJN.")
    assert extract_resultado(t) == "confirma"


def test_competence_and_extraordinary_appeal_rulings():
    assert extract_resultado(PAD + "el Tribunal RESUELVE: Atribuir la competencia para entender en los presentes autos "
                                   "al Juzgado Federal de Ejecuciones Fiscales Tributarias n° 5.") == "competencia"
    assert extract_resultado(PAD + "el Tribunal RESUELVE: Denegar el recurso extraordinario federal interpuesto.") == "rechaza"
    assert extract_resultado(PAD + "el Tribunal RESUELVE: Declarar inadmisible el recurso interpuesto.") == "rechaza"


def test_asi_se_resuelve_split_by_the_pdf_is_a_closing_not_an_opening():
    # CNACAF: the decision comes first and "ASÍ SE RESUELVE" closes it; the PDF often breaks the phrase
    for closing in ("ASÍ SE .\n\nRESUELVE", "Todo lo cual, ASI\n\nSE RESUELVE.", "ASÍ\n\nSE\n\nRESUELVE."):
        t = PAD + ("III.- Que transcurrió en exceso el plazo previsto en el artículo 310 del CPCCN. Por lo tanto, "
                   "corresponde revocar la resolución apelada. " + closing +
                   " Se deja constancia de que la Vocalía N° 15 se encuentra vacante. Regístrese y devuélvase.")
        assert extract_resultado(t) == "revoca", closing


def test_expediente_in_the_heading_prefers_the_court_number_over_the_administrative_file():
    # CNACAF carátulas carry the agency file: "DNM c/ FERNANDEZ - EXPTE 2151497/06 s/MEDIDAS DE RETENCION"
    head = ("CAMARA CONTENCIOSO ADMINISTRATIVO FEDERAL - SALA IV – CAF 17946/2025/CA3 “DNM c/ FERNANDEZ ROBLES, "
            "JAIRO ALEXANDER- EXPTE 2151497/06 s/MEDIDAS DE RETENCION” Buenos Aires, febrero de 2026")
    assert extract_expediente_texto(head) == "17946/2025"
    assert extract_expediente_texto("YEREN, SOLANO LUIS c/ EN-M INTERIOR-DNM-EXPTE 3074/15 s/RECURSO DIRECTO DNM") == ""


# -- blind review of the new fueros (2026-09-30) ---------------------------------------------

def test_ordering_the_enforcement_to_proceed_grants_the_claim():
    # Juzgados de Ejecuciones Fiscales Tributarias and comercial "ejecutivo" rulings
    assert extract_resultado(PAD + "Por ello, FALLO: 1) Mandando llevar adelante la ejecución hasta hacer íntegro pago.") == "hace lugar"
    assert extract_resultado(PAD + "RESUELVO: Mandar llevar adelante la ejecución contra el demandado.") == "hace lugar"


def test_declaring_it_unnecessary_to_rule_is_abstracto():
    assert extract_resultado(PAD + "el Tribunal RESUELVE: 1) Declarar inoficioso pronunciarse sobre el recurso.") == "abstracto"


def test_rejecting_the_counterclaim_is_not_rejecting_the_claim():
    t = PAD + "Por ello, FALLO: 1) Rechazando la reconvención intentada y haciendo lugar parcialmente a la demanda."
    assert extract_resultado(t) == "hace lugar"


def test_raising_or_lowering_the_amounts_modifies_the_ruling():
    # Cámara Civil: "1) Elevar la suma reconocida por incapacidad física… 2) Incrementar el monto…"
    assert extract_resultado(PAD + "SE RESUELVE: 1) Elevar la suma reconocida por incapacidad física a $15.300.000; "
                                   "2) Incrementar el monto por daño psicológico.") == "modifica"
    assert extract_resultado(PAD + "SE RESUELVE: 1) Admitir parcialmente las quejas de la actora, y en su virtud, elevar al "
                                   "monto de $5.400.000 las cantidades reconocidas; 2) Confirmar en lo demás.") == "modifica"
    assert extract_resultado(PAD + "SE RESUELVE: 1) Reducir la indemnización por daño moral a $2.000.000.") == "modifica"


def test_commercial_chamber_votes_with_a_comma_after_the_title():
    t = ("A la cuestión propuesta el señor Juez de Cámara, doctor Pablo D. Heredia dijo: 1°) La sentencia rechazó. "
         "El señor Juez de Cámara, doctor Eduardo R. Machin dijo: Adhiero.")
    assert extract_votos(t) == ["Pablo D. Heredia", "Eduardo R. Machin"]


def test_short_enforcement_rulings_decide_at_the_start():
    # Juzgado Comercial 12, "ejecutivo": the decision is in the first paragraph, there is no FALLO/RESUELVO
    t = ("SEOANE c/ CHOQUE s/EJECUTIVO. VISTOS Y CONSIDERANDO: No habiendo opuesto excepciones válidas, sentencio este "
         "juicio de trance y remate conforme los arts. 542, 551 y 558 del Código Procesal, mandando llevar adelante la "
         "ejecución contra Choque Alan hasta hacerse al acreedor íntegro pago del capital reclamado. " + PAD)
    assert extract_resultado(t) == "hace lugar"
    assert extract_resultado(PAD + "Por ello, FALLO: I) Mandando a seguir adelante la ejecución de sentencia contra la "
                                   "demandada Estado Nacional hasta hacer íntegro el pago.") == "hace lugar"


# -- Checked against notes written by people (Microjuris, Diario Judicial, CNACAF bulletins), 2026-10-01 ------

def test_norms_cited_as_a_list_keep_every_article():
    t = ("tras repasar doctrina, jurisprudencia y normas (art. 377 de la ley Nº 19.550 y arts. 1463 y 1467 del CCyCN) "
         "sobre naturaleza; Fallos: 258:304; art. 386, última parte, del C.P.C.C.N.; (cfr. arts. 330 inc. 2 y 377 del "
         "C.P.C.C.N.). Costas (cfr. arts. 68 y 71 del C.P.C.C.N.).")
    normas = extract_normas(t)
    assert {"CCyC art. 1463", "CCyC art. 1467", "CPCCN art. 386", "CPCCN art. 330", "CPCCN art. 377",
            "CPCCN art. 68", "CPCCN art. 71", "ley 19.550"} <= set(normas)
    assert "CCyC art. 377" not in normas            # that 377 is of the ley 19.550
    assert "CPCCN art. 2" not in normas             # "inc. 2" is an inciso, not an article


def test_norms_list_with_ranges_and_bis():
    assert {"CCyC art. 1737", "CCyC art. 1740", "CCyC art. 1741"} <= set(
        extract_normas("(arts. 1737 a 1740 y 1741 del Código Civil y Comercial de la Nación)"))
    assert "LCT art. 245" in extract_normas("la indemnización de los arts. 232, 233 y 245 bis de la LCT")


def test_a_partial_dissent_makes_the_ruling_by_majority():
    signed = PAD + ("Por los fundamentos del acuerdo precedente, y con la disidencia parcial de la doctora María "
                    "Guadalupe Vásquez, se RESUELVE: confirmar la sentencia apelada. Pablo D. Heredia (en disidencia "
                    "parcial) Ernesto Lucchelli Eduardo R. Machín")
    assert por_mayoria(signed)
    third = PAD + "EL DR. MARIO S. FERA DIJO: En lo que es materia de disidencia, me adhiero al primer voto." + PAD + \
        "Por ello, el Tribunal RESUELVE: 1) Confirmar la sentencia."
    assert por_mayoria(third)
    disagree = PAD + "EL DOCTOR VICTOR ARTURO PESINO DIJO: I.- Discrepo del voto que antecede en cuanto propone " \
                     "confirmar la condena." + PAD + "el Tribunal RESUELVE: 1) Modificar la sentencia."
    assert por_mayoria(disagree)
    assert por_mayoria(RIVAS) is False             # "una mera disidencia de lo resuelto" is the appellant's, not a vote


def test_deserting_the_appeal_is_desierto():
    t = PAD + ("el Tribunal resuelve: 1) Decretar la deserción del recurso de apelación interpuesto; 2) Confirmar la "
               "sentencia de grado en todo lo que ha sido motivo de agravio.")
    assert extract_resultado(t) == "desierto"


def test_admitting_the_appeal_in_part_grants_it():
    t = PAD + ("Por ello, SE RESUELVE: a) admitir parcialmente el recurso intentado por la demandada en los términos "
               "que surgen del presente; b) imponer las costas por su orden.")
    assert extract_resultado(t) == "hace lugar"


def test_decide_after_a_stray_colon_opens_the_resolutive_part():
    t = PAD + ("Y VISTOS lo deliberado y conclusiones establecidas en el Acuerdo precedentemente transcripto el "
               "tribunal : decide Revocar 1) la sentencia; y hacer lugar parcialmente a la demanda; 2) fijar la partida.")
    assert extract_resultado(t) == "revoca"


def test_the_pdf_that_moves_resuelve_after_the_first_item():
    t = PAD + ("ya que la parte demandada resultó totalmente vencida, corresponde rechazar el agravio, con costas (conf. "
               "art. 68, primer párrafo y 69 del CPCCN). "
               "En virtud de todo lo expuesto, SE : Declarar desierto el recurso de apelación interpuesto RESUELVE "
               "por la parte demandada (art. 266 del CPCCN); con costas (art. 68 del CPCCN). Regístrese.")
    assert extract_resultado(t) == "desierto"


def test_article_numbers_written_with_a_degree_sign():
    assert extract_normas("es de destacar que el art. 7° del Código Civil y Comercial de la Nación dispone") == ["CCyC art. 7"]
    assert extract_normas("(arts. 804 CCCN y 37 CPCCN)") == ["CCyC art. 804"]      # 37 sits after the code that closes it


def test_granting_the_appeal_reads_as_its_consequence():
    t = PAD + "SE RESUELVE: 1) Admitir el recurso de apelación y, en consecuencia, revocar la sentencia apelada; 2) Costas."
    assert extract_resultado(t) == "revoca"
    t = PAD + "el Tribunal RESUELVE: hacer lugar parcialmente al recurso y modificar la sentencia en cuanto a los intereses."
    assert extract_resultado(t) == "modifica"


def test_the_dissent_of_another_case_cited_in_a_footnote_is_not_this_ones():
    t = PAD + ("el Tribunal RESUELVE: 1) Confirmar la sentencia. Regístrese. JUAN PEREZ PEDRO GOMEZ. 18 ver voto del "
               "Dr. Galmarini en la disidencia efectuada en la c. 97.631-09 del 27-5-19")
    assert por_mayoria(t) is False


def test_the_consequence_of_granting_the_appeal_can_be_the_next_item():
    t = PAD + ("Por ello, se RESUELVE: i) admitir el recurso interpuesto por la parte actora a fs. 376; ii) modificar la "
               "sentencia dictada a fs. 371/374 con el único alcance de reconocer el daño punitivo; y iii) costas.")
    assert extract_resultado(t) == "modifica"
    t = PAD + ("SE RESUELVE: 1°) admitir parcialmente el recurso de apelación interpuesto por la demandada, en los "
               "términos de los Considerandos VIII a X; y 2º) distribuir las costas en el orden causado.")
    assert extract_resultado(t) == "hace lugar"


def test_procedural_code_by_its_other_names():
    assert extract_normas("en uso de las facultades conferidas por el art. 165 del Cód. Procesal") == ["CPCCN art. 165"]
    assert extract_normas("el principio general que sienta el art. 386 del ordenamiento adjetivo") == ["CPCCN art. 386"]
    assert extract_normas("conforme el art. 477 del código ritual") == ["CPCCN art. 477"]
    assert extract_normas("Con costas de alzada a la apelante, vencida (art 68 del Código Procesal).") == ["CPCCN art. 68"]
    assert extract_normas("art. 15 del Código Procesal Penal") == []


# -- Checked against the second, unseen round of notes (2026-10-01) ------------------------------------------

def test_more_ways_to_write_a_split_vote():
    settle = PAD + ("El Dr. Leonardo Jesús Ambesi dijo: En lo que resulta materia de disidencia entre mis distinguidos "
                    "colegas, adhiero al voto del Dr. Sudera." + PAD + "el Tribunal RESUELVE: 1) Confirmar la sentencia.")
    assert por_mayoria(settle)
    called = PAD + "He sido convocado a zanjar tal disidencia y así lo haré." + PAD + "el Tribunal RESUELVE: 1) Revocar."
    assert por_mayoria(called)
    reasons = PAD + ("Atento lo que resulta del acuerdo que antecede, y las razones que fundan el voto de la mayoría, "
                     "SE RESUELVE: 1) Revocar la sentencia de grado.")
    assert por_mayoria(reasons)
    assert not por_mayoria(PAD + "adhiero a la tesis de la mayoría de las Salas de esta Cámara." + PAD +
                           "el Tribunal RESUELVE: 1) Confirmar la sentencia.")


def test_raising_an_amount_with_aumentar_modifies():
    t = PAD + ("SE RESUELVE: I) aumentar a Pesos Cinco Millones ($5.000.000) la suma fijada en concepto de valor vida, "
               "II) confirmar la sentencia en todo lo demás.")
    assert extract_resultado(t) == "modifica"


def test_a_verb_split_by_the_pdf():
    t = PAD + "SE RESUELVE: r evocar la sentencia de grado en lo sustancial haciendo lugar al recurso del actor."
    assert extract_resultado(t) == "revoca"
    t = PAD + "SE RESUELVE: r echazar el recurso de la actora y confirmar la sentencia apelada en todos sus términos."
    assert extract_resultado(t) == "confirma"


def test_rejecting_the_appeal_then_confirming_in_the_next_item():
    t = PAD + ("Por ello, se RESUELVE: (i) rechazar los recursos interpuestos por ambas partes y, en consecuencia; "
               "(ii) confirmar la sentencia apelada; (iii) costas en el orden causado.")
    assert extract_resultado(t) == "confirma"
    t = PAD + "SE RESUELVE: 1) Rechazar la demanda contra Pérez; 2) Confirmar la sentencia en lo demás."
    assert extract_resultado(t) == "rechaza"          # rejecting a claim is not rejecting an appeal


def test_first_instance_whose_pdf_moved_fallo_after_the_gerund():
    t = PAD + ("Por lo expuesto, disposiciones legales, doctrina y jurisprudencia citadas, Admitiendo :\n\nFALLO "
               "parcialmente la demanda deducida. En consecuencia, se condena a Edesur.")
    assert extract_resultado(t) == "hace lugar"


def test_an_appeal_wrongly_granted_stays_rejected_even_if_fees_are_confirmed():
    t = PAD + ("el Tribunal RESUELVE: I) Declarar mal concedido e recurso; II) Confirmar lo decidido en materia de costas "
               "y honorarios; III) Imponer las costas de alzada a la demandada.")
    assert extract_resultado(t) == "rechaza"


def test_rejecting_one_appeal_and_granting_the_other_reads_as_what_changes():
    t = PAD + ("Por ello, se RESUELVE: i) rechazar el recurso de la demandada de fs. 912; ii) admitir parcialmente el "
               "recurso del actor de fs. 914 y, en consecuencia, elevar el monto reconocido en concepto de daño moral "
               "a la suma de $ 3.000.000; iii) costas a la demandada.")
    assert extract_resultado(t) == "modifica"
