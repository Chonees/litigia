"""What a human-written note says about a ruling is compared with the fields we extracted."""

from spikes.compare_with_notes import dates_agree, judge_signs, norm_found, result_agrees


def test_the_same_result_agrees_and_partial_confirmations_are_gray():
    assert result_agrees("confirma", False, "confirma") == "coincide"
    assert result_agrees("revoca", False, "confirma") == "no coincide"
    # "confirmó parcialmente" or "modificó los intereses": either reading of the first resolutive item is fair
    assert result_agrees("confirma", True, "modifica") == "zona gris"
    assert result_agrees("modifica", False, "confirma") == "zona gris"
    assert result_agrees("hace lugar", True, "rechaza") == "zona gris"
    assert result_agrees("no lo dice", False, "confirma") is None


def test_norms_the_note_names_are_looked_up_in_ours():
    ours = ["LCT art. 105", "ley 24.240", "CCyC art. 1757", "CPCCN art. 68"]
    assert norm_found({"cuerpo": "LCT", "ley": "", "articulo": "105"}, ours)
    assert norm_found({"cuerpo": "ley", "ley": "24.240", "articulo": "52 bis"}, ours)
    assert norm_found({"cuerpo": "ley", "ley": "24240", "articulo": ""}, ours)
    assert not norm_found({"cuerpo": "CCyC", "ley": "", "articulo": "1758"}, ours)
    assert norm_found({"cuerpo": "otra", "ley": "", "articulo": ""}, ours) is None


def test_a_judge_named_by_the_note_signs_with_full_name():
    firmantes = ["LORENA FERNANDA MAGGIO", "ROBERTO PARRILLI", "CLAUDIO RAMOS FEIJOO"]
    assert judge_signs("Maggio", firmantes)
    assert judge_signs("Ramos Feijóo", firmantes)
    assert not judge_signs("Pesino", firmantes)


def test_dates_agree_within_a_week_or_by_month_when_the_note_gives_only_the_month():
    assert dates_agree("2026-03-18", "2026-03-19")
    assert not dates_agree("2026-09-17", "2026-08-31")
    assert dates_agree("2026-04", "2026-04-17")
    assert not dates_agree("2026-09", "2026-08-04")
