"""How good is a labeler: accuracy above a confidence threshold, calibration, consistency."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class Answer:
    item: str           # fallo id
    predicted: str
    confidence: float
    gold: object        # a value, or a set of acceptable values


def is_correct(predicted: str, gold: object) -> bool:
    if isinstance(gold, (set, frozenset, list, tuple)):
        return predicted in gold
    return predicted == gold


def at_threshold(answers: list[Answer], threshold: float) -> dict:
    """Coverage = share of answers at or above the threshold; accuracy = among those."""
    passed = [a for a in answers if a.confidence >= threshold]
    correct = sum(is_correct(a.predicted, a.gold) for a in passed)
    return {
        "threshold": threshold,
        "coverage": len(passed) / len(answers) if answers else 0.0,
        "accuracy": correct / len(passed) if passed else None,
        "n": len(answers),
        "passed": len(passed),
    }


def calibration(answers: list[Answer], edges: Iterable[float] = (0.0, 0.5, 0.7, 0.9, 1.0001)) -> list[dict]:
    """Does 0.9 confidence mean ~90% correct? Accuracy per confidence bin."""
    edges = list(edges)
    out = []
    for lo, hi in zip(edges, edges[1:]):
        group = [a for a in answers if lo <= a.confidence < hi]
        if not group:
            continue
        out.append({
            "bin": f"{lo:.2f}-{min(hi, 1.0):.2f}",
            "n": len(group),
            "mean_confidence": sum(a.confidence for a in group) / len(group),
            "accuracy": sum(is_correct(a.predicted, a.gold) for a in group) / len(group),
        })
    return out


def consistency(runs: list[dict[str, tuple[str, float]]], threshold: float | None = None) -> float:
    """Share of items that get the same answer in every run.

    With a threshold, an answer below it counts as "uncertain" — the label the
    application would store — so wobbling between two low-confidence options is stable.
    """
    items = set(runs[0])
    for run in runs[1:]:
        items &= set(run)

    def label(pred: str, conf: float) -> str:
        return "uncertain" if threshold is not None and conf < threshold else pred

    stable = sum(1 for i in items if len({label(*run[i]) for run in runs}) == 1)
    return stable / len(items) if items else 0.0
