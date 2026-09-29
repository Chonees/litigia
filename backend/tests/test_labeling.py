"""Labeling building blocks: the state sent to the labeler and the metrics that judge it."""

from scripts.labeling.metrics import Answer, at_threshold, calibration, consistency, is_correct
from scripts.labeling.state import build_state

DOC = {
    "caratula": "SOSA c/ ACME S.A. s/DESPIDO",
    "objeto": "DESPIDO",
    "tribunal": "CÁMARA NACIONAL DE APELACIONES DEL TRABAJO - SALA IV",
    "fecha": "2024-03-04",
    "expediente": "CNT 049971/2016/CA001",
    "texto": "SENTENCIA DEFINITIVA\n\nI) Se agravia la demandada.\n\nII) Corresponde confirmar.\n\nRESUELVE: confirmar.",
}


# -- state ----------------------------------------------------------------------

def test_state_numbers_every_paragraph():
    state = build_state(DOC)
    assert list(state["parrafos"]) == ["p0", "p1", "p2", "p3"]
    assert state["parrafos"]["p1"] == "I) Se agravia la demandada."
    assert state["caratula"] == DOC["caratula"]
    assert state["tribunal"] == DOC["tribunal"]


def test_filtered_state_keeps_original_paragraph_ids():
    state = build_state(DOC, keep=lambda i, p: "agravia" in p or "RESUELVE" in p)
    assert list(state["parrafos"]) == ["p1", "p3"]


def test_state_has_no_empty_fields():
    state = build_state({**DOC, "expediente": ""})
    assert "expediente" not in state


# -- metrics ----------------------------------------------------------------------

def test_is_correct_accepts_a_set_of_valid_answers():
    assert is_correct("p5", {"p5", "p6"})
    assert not is_correct("p2", {"p5", "p6"})
    assert is_correct("confirma", "confirma")


def test_at_threshold_reports_coverage_and_accuracy_of_what_passes():
    answers = [
        Answer("a", "x", 0.95, "x"),
        Answer("b", "x", 0.90, "y"),
        Answer("c", "y", 0.40, "y"),
        Answer("d", "y", 0.99, "y"),
    ]
    r = at_threshold(answers, 0.8)
    assert r == {"threshold": 0.8, "coverage": 0.75, "accuracy": 2 / 3, "n": 4, "passed": 3}


def test_at_threshold_with_nothing_passing():
    assert at_threshold([Answer("a", "x", 0.1, "x")], 0.9)["accuracy"] is None


def test_calibration_groups_by_confidence():
    answers = [Answer(str(i), "x", 0.95, "x" if i < 9 else "y") for i in range(10)]
    answers += [Answer(f"l{i}", "x", 0.55, "x" if i < 5 else "y") for i in range(10)]
    bins = {b["bin"]: b for b in calibration(answers, edges=(0.0, 0.5, 0.9, 1.0001))}
    assert bins["0.90-1.00"]["n"] == 10 and bins["0.90-1.00"]["accuracy"] == 0.9
    assert bins["0.50-0.90"]["n"] == 10 and bins["0.50-0.90"]["accuracy"] == 0.5


def test_consistency_counts_items_whose_answer_never_changes():
    runs = [
        {"a": ("x", 0.9), "b": ("x", 0.9), "c": ("x", 0.5)},
        {"a": ("x", 0.9), "b": ("y", 0.9), "c": ("y", 0.5)},
    ]
    assert consistency(runs) == 1 / 3
    # Below the threshold an answer becomes "uncertain" in every run, which is stable.
    assert consistency(runs, threshold=0.6) == 2 / 3
