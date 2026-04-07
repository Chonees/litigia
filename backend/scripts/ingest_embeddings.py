"""Ingest cleaned documents into Qdrant with embeddings.

Reads JSONL files from data/, generates embeddings, and upserts to Qdrant.

Usage:
    python -m scripts.ingest_embeddings [--batch-size 50] [--max-docs 1000]
"""

import argparse
import asyncio
import json
from pathlib import Path

from app.services.embeddings import get_embeddings
from app.services.vector_store import ensure_collection, get_qdrant_client, upsert_documents

DATA_DIR = Path(__file__).parent.parent / "data"
MAX_CHUNK_TOKENS = 1000  # approximate, using char count / 4


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    """Split text into chunks, trying to break at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text[:max_chars]]


async def ingest_file(filepath: Path, batch_size: int = 50, max_docs: int | None = None):
    """Ingest a single JSONL file into Qdrant."""
    client = get_qdrant_client()
    ensure_collection(client)

    print(f"\nIngesting {filepath.name}...")

    docs_batch: list[dict] = []
    texts_batch: list[str] = []
    total_ingested = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            if max_docs and total_ingested >= max_docs:
                break

            doc = json.loads(line)
            texto = doc["texto"]

            # Chunk long documents
            chunks = chunk_text(texto)

            for chunk_idx, chunk in enumerate(chunks):
                chunk_doc = {
                    **doc,
                    "id": f"{doc['id']}_{chunk_idx}" if len(chunks) > 1 else doc["id"],
                    "texto": chunk,
                }

                # Text for embedding: combine metadata + content
                embed_text = f"{doc.get('caratula', '')} {doc.get('materia', '')} {chunk}"
                texts_batch.append(embed_text[:8000])  # OpenAI limit
                docs_batch.append(chunk_doc)

                if len(docs_batch) >= batch_size:
                    embeddings = await get_embeddings(texts_batch)
                    await upsert_documents(docs_batch, embeddings, client)
                    total_ingested += len(docs_batch)
                    print(f"  Ingested {total_ingested} chunks...")
                    docs_batch = []
                    texts_batch = []

    # Final batch
    if docs_batch:
        embeddings = await get_embeddings(texts_batch)
        await upsert_documents(docs_batch, embeddings, client)
        total_ingested += len(docs_batch)

    print(f"  Total: {total_ingested} chunks ingested from {filepath.name}")
    return total_ingested


async def main(batch_size: int, max_docs: int | None):
    total = 0
    for jsonl_file in sorted(DATA_DIR.glob("*.jsonl")):
        count = await ingest_file(jsonl_file, batch_size, max_docs)
        total += count

    print(f"\nDone! Total chunks ingested: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--max-docs", type=int, default=None)
    args = parser.parse_args()

    asyncio.run(main(args.batch_size, args.max_docs))
