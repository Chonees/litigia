"""Vote structure of a Cámara ruling, detected in code (who voted where, who is the majority)."""

from scripts.labeling.votes import detect_votes

DISSENT = [
    "SENTENCIA DEFINITIVA ... se procede a votar en el siguiente orden: EL DOCTOR CARLOS POSE DIJO:",
    "I.- La demandada apela la sentencia.",
    "II.- Corresponde reducir la incapacidad psicológica.",
    "Propongo modificar la sentencia. LA DOCTORA GRACIELA L. CRAIG DIJO:",
    "Disiento respetuosamente con el voto de mi distinguido colega, el Dr. Pose.",
    "Por ello, propongo confirmar la sentencia.",
    "LA DOCTORA GABRIELA ALEJANDRA VAZQUEZ DIJO:",
    "En lo que ha sido materia de disidencia entre mis colegas, adhiero al voto de la Dra. Craig.",
    "Por lo que resulta del acuerdo que antecede, el TRIBUNAL RESUELVE: 1) Confirmar la sentencia.",
]

UNANIMOUS = [
    "SENTENCIA DEFINITIVA ... LA DOCTORA SILVIA E. PINTO VARELA DIJO:",
    "I) Contra la sentencia se alzan ambas partes.",
    "II) Corresponde confirmar.",
    "El doctor Héctor C. Guisado dijo:",
    "Por análogos fundamentos adhiero al voto que antecede.",
    "Por ello, el Tribunal RESUELVE: 1) Confirmar la sentencia apelada.",
]


def test_votes_are_segmented_by_the_dijo_lines():
    v = detect_votes(DISSENT)
    assert [x["juez"] for x in v["votos"]] == ["CARLOS POSE", "GRACIELA L. CRAIG", "GABRIELA ALEJANDRA VAZQUEZ"]
    assert v["votos"][0]["parrafos"] == ["p1", "p2", "p3"]
    assert v["votos"][1]["parrafos"] == ["p4", "p5"]
    assert v["votos"][2]["parrafos"] == ["p6", "p7"]


def test_dissent_majority_is_the_vote_the_third_judge_joins():
    v = detect_votes(DISSENT)
    assert v["hay_disidencia"] is True
    assert v["voto_mayoria"] == "GRACIELA L. CRAIG"
    assert v["votos_minoria"] == ["CARLOS POSE"]


def test_unanimous_ruling_follows_the_first_vote():
    v = detect_votes(UNANIMOUS)
    assert v["hay_disidencia"] is False
    assert v["voto_mayoria"] == "SILVIA E. PINTO VARELA"
    assert v["votos_minoria"] == []
    assert [x["juez"] for x in v["votos"]] == ["SILVIA E. PINTO VARELA", "Héctor C. Guisado"]


def test_ruling_without_votes():
    v = detect_votes(["VISTO Y CONSIDERANDO:", "Que corresponde declarar abstracta la cuestión.", "RESUELVE: archivar."])
    assert v == {"votos": [], "hay_disidencia": False, "voto_mayoria": "", "votos_minoria": []}


IMPLICIT_DISSENT = [
    "SENTENCIA DEFINITIVA ... LA DOCTORA GRACIELA L. CRAIG DIJO:",
    "I.- La demandada cuestiona la incapacidad.",
    "Por ello, voto por confirmar la sentencia en todo lo que fue materia de agravios.",
    "EL DOCTOR CARLOS POSE DIJO:",
    "La incapacidad psicológica no guarda relación con el daño físico.",
    "En definitiva, propicio modificar la incapacidad dictaminada en grado y fijarla en el 24,46%.",
    "Adhiero al voto de la Dra. Graciela L. Craig. Por lo que resulta del acuerdo que antecede, "
    "el TRIBUNAL RESUELVE: I) Confirmar la sentencia.",
]


def test_implicit_dissent_when_two_votes_propose_different_outcomes():
    v = detect_votes(IMPLICIT_DISSENT)
    assert v["hay_disidencia"] is True
    assert v["voto_mayoria"] == "GRACIELA L. CRAIG"
    assert v["votos_minoria"] == ["CARLOS POSE"]


def test_judge_name_stops_at_the_next_judge():
    v = detect_votes(["Adhiero al voto de la Dra. Graciela L. Craig. LA DOCTORA GABRIELA ALEJANDRA VAZQUEZ DIJO:", "x"])
    assert v["votos"][0]["juez"] == "GABRIELA ALEJANDRA VAZQUEZ"


def test_votes_headed_with_manifesto_count():
    v = detect_votes(["EL DOCTOR GABRIEL DE VEDIA DIJO:", "Propongo confirmar.", "LA DOCTORA BEATRIZ E. FERDMAN MANIFESTÓ:",
                      "Que adhiero al voto que antecede.", "Por ello, el TRIBUNAL RESUELVE: confirmar."])
    assert [x["juez"] for x in v["votos"]] == ["GABRIEL DE VEDIA", "BEATRIZ E. FERDMAN"]


def test_vote_headings_with_comma_or_without_colon():
    v = detect_votes(["El Dr. LEONADO J. AMBESI dijo:", "Propongo modificar.",
                      "La Dra. MARÍA CECILIA HOCKL, dijo: En cuanto a los agravios, adhiero.",
                      "Por ello, el TRIBUNAL RESUELVE: modificar."])
    assert [x["juez"].split()[-1].upper() for x in v["votos"]] == ["AMBESI", "HOCKL"]
