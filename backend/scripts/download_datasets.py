"""Download and clean legal datasets from HuggingFace.

Datasets:
- marianbasti/jurisprudencia-Argentina-SAIJ: 900k+ docs (fallos, legislation, doctrine)
- harpomaxx/jurisgpt: Labor law rulings with summaries

Usage:
    python -m scripts.download_datasets
"""

import json
import hashlib
from pathlib import Path

from datasets import load_dataset

DATA_DIR = Path(__file__).parent.parent / "data"
SAIJ_OUTPUT = DATA_DIR / "saij_cleaned.jsonl"
JURISGPT_OUTPUT = DATA_DIR / "jurisgpt_cleaned.jsonl"


def generate_id(text: str) -> str:
    """Generate a deterministic ID from text content."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def clean_saij():
    """Download and clean SAIJ dataset."""
    print("Downloading SAIJ dataset (this may take a while)...")
    ds = load_dataset("marianbasti/jurisprudencia-Argentina-SAIJ", split="train")

    print(f"SAIJ: {len(ds)} documents loaded")

    count = 0
    with open(SAIJ_OUTPUT, "w", encoding="utf-8") as f:
        for row in ds:
            # Extract and normalize fields
            texto = row.get("texto", "") or row.get("text", "") or ""
            if not texto or len(texto) < 100:
                continue

            doc = {
                "id": generate_id(texto),
                "source": "saij",
                "source_id": row.get("id", ""),
                "tipo": row.get("tipo", "") or row.get("type", ""),
                "tribunal": row.get("tribunal", "") or "",
                "fecha": row.get("fecha", "") or row.get("date", "") or "",
                "caratula": row.get("caratula", "") or row.get("title", "") or "",
                "texto": texto,
                "materia": row.get("materia", "") or "",
                "voces": row.get("voces", []) or [],
                "fuero": row.get("fuero", "") or "",
                "jurisdiccion": row.get("jurisdiccion", "") or "",
            }

            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            count += 1

            if count % 10000 == 0:
                print(f"  Processed {count} documents...")

    print(f"SAIJ: {count} valid documents saved to {SAIJ_OUTPUT}")


def clean_jurisgpt():
    """Download and clean JurisGPT dataset."""
    print("Downloading JurisGPT dataset...")
    ds = load_dataset("harpomaxx/jurisgpt", split="train")

    print(f"JurisGPT: {len(ds)} documents loaded")

    count = 0
    with open(JURISGPT_OUTPUT, "w", encoding="utf-8") as f:
        for row in ds:
            texto = row.get("sentencia", "") or row.get("text", "") or ""
            if not texto or len(texto) < 100:
                continue

            doc = {
                "id": generate_id(texto),
                "source": "jurisgpt",
                "source_id": row.get("id", ""),
                "tipo": "fallo",
                "tribunal": row.get("tribunal", "") or "",
                "fecha": row.get("fecha", "") or "",
                "caratula": row.get("caratula", "") or row.get("sumario", "")[:100] or "",
                "texto": texto,
                "materia": row.get("materia", "") or "laboral",
                "voces": row.get("voces", []) or [],
                "fuero": "laboral",
                "jurisdiccion": row.get("jurisdiccion", "") or "",
            }

            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            count += 1

    print(f"JurisGPT: {count} valid documents saved to {JURISGPT_OUTPUT}")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_saij()
    clean_jurisgpt()
    print("\nDone! Run scripts/ingest_embeddings.py next.")
