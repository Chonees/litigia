"""The state a labeler reads: fallo metadata plus its paragraphs, numbered p0, p1, …

Paragraph ids are stable (they index the stored text), so a label can point at the
paragraph that supports it, and a filtered state keeps the original ids.
"""

from typing import Callable

from scripts import quality

META = ("expediente", "caratula", "objeto", "tribunal", "fecha")


def build_state(doc: dict, keep: Callable[[int, str], bool] | None = None) -> dict:
    paragraphs = quality.split_paragraphs(doc.get("texto") or "")
    state = {k: doc[k] for k in META if doc.get(k)}
    state["parrafos"] = {
        f"p{i}": p for i, p in enumerate(paragraphs) if keep is None or keep(i, p)
    }
    return state
