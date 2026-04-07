"""Ingest normalized documents into Qdrant with embeddings.

Reads JSONL from D:/litigia-data/clean/, chunks long documents,
generates embeddings via OpenAI, and upserts to Qdrant.

Supports resume: tracks which documents have been ingested via checkpoint files.

Usage:
    python -m scripts.ingest_embeddings                        # all files
    python -m scripts.ingest_embeddings --source jurisgpt      # one source
    python -m scripts.ingest_embeddings --limit 500            # cap for testing
    python -m scripts.ingest_embeddings --dry-run              # show what would happen
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.embeddings import get_embeddings
from app.services.vector_store import ensure_collection, get_qdrant_client
from scripts.normalizers.schema import LitigiaDocument

from qdrant_client.models import PointStruct


def chunk_document(doc: LitigiaDocument) -> list[LitigiaDocument]:
    """Split a long document into chunks, preserving metadata.

    Tries to break at paragraph boundaries. Each chunk gets the same
    metadata but different id suffix and chunk_index.
    """
    max_chars = settings.chunk_max_chars
    texto = doc.texto

    if len(texto) <= max_chars:
        doc.total_chunks = 1
        doc.chunk_index = 0
        return [doc]

    # Split at paragraph boundaries
    paragraphs = texto.split("\n\n")
    chunks_text: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks_text.append(current.strip())
            # If a single paragraph is too long, split at sentence boundaries
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                sub_current = ""
                for sent in sentences:
                    if len(sub_current) + len(sent) + 1 > max_chars:
                        if sub_current:
                            chunks_text.append(sub_current.strip())
                        sub_current = sent
                    else:
                        sub_current += " " + sent if sub_current else sent
                current = sub_current
            else:
                current = para
        else:
            current += "\n\n" + para if current else para

    if current.strip():
        chunks_text.append(current.strip())

    if not chunks_text:
        chunks_text = [texto[:max_chars]]

    # Create a LitigiaDocument for each chunk
    result = []
    for i, chunk_text in enumerate(chunks_text):
        chunk_doc = LitigiaDocument.from_dict(doc.to_dict())
        chunk_doc.id = f"{doc.id}_c{i}" if len(chunks_text) > 1 else doc.id
        chunk_doc.texto = chunk_text
        chunk_doc.chunk_index = i
        chunk_doc.total_chunks = len(chunks_text)
        result.append(chunk_doc)

    return result


def load_checkpoint(source: str) -> set[str]:
    """Load set of already-ingested document IDs."""
    checkpoint_file = settings.data_logs / f"{source}_ingested.txt"
    if checkpoint_file.exists():
        return set(checkpoint_file.read_text().splitlines())
    return set()


def save_checkpoint(source: str, doc_ids: set[str]) -> None:
    """Append newly ingested IDs to checkpoint."""
    checkpoint_file = settings.data_logs / f"{source}_ingested.txt"
    with open(checkpoint_file, "a", encoding="utf-8") as f:
        for did in doc_ids:
            f.write(did + "\n")


async def ingest_file(
    filepath: Path,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Ingest a single JSONL file into Qdrant."""
    source = filepath.stem  # "saij" or "jurisgpt"
    already_ingested = load_checkpoint(source)
    print(f"\n  {source}: {len(already_ingested)} already ingested (will skip)")

    client = get_qdrant_client()
    ensure_collection(client)

    batch_docs: list[LitigiaDocument] = []
    batch_new_ids: set[str] = set()
    total_ingested = 0
    total_chunks = 0
    total_skipped = 0
    start = time.time()

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            if limit and total_ingested >= limit:
                break

            doc = LitigiaDocument.from_dict(json.loads(line))

            # Skip already ingested
            if doc.id in already_ingested:
                total_skipped += 1
                continue

            # Chunk the document
            chunks = chunk_document(doc)
            batch_docs.extend(chunks)
            batch_new_ids.add(doc.id)
            total_chunks += len(chunks)

            # Process batch
            if len(batch_docs) >= settings.embedding_batch_size:
                if dry_run:
                    print(f"    [DRY RUN] Would embed {len(batch_docs)} chunks")
                else:
                    await _embed_and_upsert(batch_docs, client)

                total_ingested += len(batch_new_ids)
                save_checkpoint(source, batch_new_ids)

                elapsed = time.time() - start
                print(
                    f"    {total_ingested:,} docs ({total_chunks:,} chunks) | "
                    f"{total_skipped:,} skipped | "
                    f"{elapsed:.0f}s"
                )

                batch_docs = []
                batch_new_ids = set()

    # Final batch
    if batch_docs:
        if not dry_run:
            await _embed_and_upsert(batch_docs, client)
        total_ingested += len(batch_new_ids)
        save_checkpoint(source, batch_new_ids)

    elapsed = time.time() - start
    stats = {
        "source": source,
        "ingested": total_ingested,
        "chunks": total_chunks,
        "skipped": total_skipped,
        "elapsed": round(elapsed, 1),
    }
    print(f"\n  {source} done: {json.dumps(stats)}")

    # Save ingestion stats
    stats_file = settings.data_logs / f"{source}_ingest_stats.json"
    stats_file.write_text(json.dumps(stats, indent=2))

    return stats


async def _embed_and_upsert(docs: list[LitigiaDocument], client) -> None:
    """Generate embeddings and upsert to Qdrant in one batch."""
    texts = [doc.embedding_text() for doc in docs]

    # Cap text length for OpenAI (8191 tokens ≈ 32k chars max)
    texts = [t[:8000] for t in texts]

    embeddings = await get_embeddings(texts)

    # Build Qdrant points
    points = []
    for doc, embedding in zip(docs, embeddings):
        payload = {
            "source": doc.source,
            "source_id": doc.source_id,
            "tribunal": doc.tribunal,
            "fecha": doc.fecha,
            "caratula": doc.caratula,
            "texto": doc.texto[:5000],  # cap stored text to save space
            "sumario": doc.sumario[:2000],
            "materia": doc.materia,
            "voces": doc.voces,
            "jurisdiccion": doc.jurisdiccion,
            "provincia": doc.provincia,
            "tipo_documento": doc.tipo_documento,
            "actor": doc.actor,
            "demandado": doc.demandado,
            "sobre": doc.sobre,
            "chunk_index": doc.chunk_index,
            "total_chunks": doc.total_chunks,
        }
        points.append(PointStruct(id=doc.id, vector=embedding, payload=payload))

    # Upsert in sub-batches
    batch_size = settings.qdrant_upsert_batch_size
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=settings.qdrant_collection, points=batch)


async def main(source: str | None, limit: int | None, dry_run: bool):
    settings.ensure_dirs()

    print(f"\nLITIGIA Embedding Ingestion Pipeline")
    print(f"Data: {settings.data_clean}")
    print(f"Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"Collection: {settings.qdrant_collection}")
    print(f"Embedding model: {settings.embedding_model}")
    if dry_run:
        print(f"MODE: DRY RUN (no writes)")

    all_stats = []
    for jsonl in sorted(settings.data_clean.glob("*.jsonl")):
        if source and jsonl.stem != source:
            continue
        stats = await ingest_file(jsonl, limit=limit, dry_run=dry_run)
        all_stats.append(stats)

    total_docs = sum(s["ingested"] for s in all_stats)
    total_chunks = sum(s["chunks"] for s in all_stats)
    print(f"\n{'='*60}")
    print(f"Total: {total_docs:,} documents, {total_chunks:,} chunks ingested")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LITIGIA Embedding Ingestion")
    parser.add_argument("--source", choices=["saij", "jurisgpt"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(main(args.source, args.limit, args.dry_run))
