"""Ingest normalized documents into ChromaDB with embeddings.

Reads JSONL from D:/litigia-data/clean/, chunks long documents,
generates embeddings via OpenAI, and upserts to ChromaDB.

Supports resume: tracks which documents have been ingested via checkpoint files.

Usage:
    python -m scripts.ingest_embeddings                        # all files
    python -m scripts.ingest_embeddings --source jurisgpt      # one source
    python -m scripts.ingest_embeddings --limit 500            # cap for testing
    python -m scripts.ingest_embeddings --dry-run              # show what would happen
    python -m scripts.ingest_embeddings --status               # show collection stats
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
from app.services.vector_store import get_collection, upsert_documents, collection_count
from scripts.normalizers.schema import LitigiaDocument


def chunk_document(doc: LitigiaDocument) -> list[LitigiaDocument]:
    """Split a long document into chunks, preserving metadata."""
    max_chars = settings.chunk_max_chars
    texto = doc.texto

    if len(texto) <= max_chars:
        doc.total_chunks = 1
        doc.chunk_index = 0
        return [doc]

    paragraphs = texto.split("\n\n")
    chunks_text: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current:
                chunks_text.append(current.strip())
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


def append_checkpoint(source: str, doc_ids: set[str]) -> None:
    """Append newly ingested IDs to checkpoint."""
    checkpoint_file = settings.data_logs / f"{source}_ingested.txt"
    with open(checkpoint_file, "a", encoding="utf-8") as f:
        for did in doc_ids:
            f.write(did + "\n")


def save_progress(source: str, stats: dict) -> None:
    """Save ingestion progress to JSON."""
    progress_file = settings.data_logs / f"{source}_ingest_progress.json"
    progress_file.write_text(json.dumps(stats, indent=2))


async def _embed_and_upsert(docs: list[LitigiaDocument]) -> None:
    """Generate embeddings and upsert to ChromaDB."""
    texts = [doc.embedding_text()[:8000] for doc in docs]

    embeddings = await get_embeddings(texts)

    doc_ids = [doc.id for doc in docs]
    documents = [doc.texto[:5000] for doc in docs]
    metadatas = [
        {
            "source": doc.source,
            "source_id": doc.source_id,
            "tribunal": doc.tribunal,
            "fecha": doc.fecha,
            "caratula": doc.caratula,
            "sumario": doc.sumario[:2000] if doc.sumario else "",
            "materia": doc.materia,
            "voces": ", ".join(doc.voces[:10]),
            "jurisdiccion": doc.jurisdiccion,
            "provincia": doc.provincia,
            "tipo_documento": doc.tipo_documento,
            "actor": doc.actor,
            "demandado": doc.demandado,
            "sobre": doc.sobre,
            "chunk_index": doc.chunk_index,
            "total_chunks": doc.total_chunks,
        }
        for doc in docs
    ]

    await upsert_documents(doc_ids, embeddings, documents, metadatas)


async def ingest_file(
    filepath: Path,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Ingest a single JSONL file into ChromaDB."""
    source = filepath.stem
    already_ingested = load_checkpoint(source)
    print(f"\n  {source}: {len(already_ingested):,} already ingested (will skip)")

    batch_docs: list[LitigiaDocument] = []
    batch_new_ids: set[str] = set()
    total_ingested = 0
    total_chunks = 0
    total_skipped = 0
    start = time.time()

    # Count total for progress
    total_lines = sum(1 for _ in open(filepath, encoding="utf-8"))
    print(f"  {source}: {total_lines:,} documents to process")

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            if limit and total_ingested >= limit:
                break

            doc = LitigiaDocument.from_dict(json.loads(line))

            if doc.id in already_ingested:
                total_skipped += 1
                continue

            chunks = chunk_document(doc)
            batch_docs.extend(chunks)
            batch_new_ids.add(doc.id)
            total_chunks += len(chunks)

            if len(batch_docs) >= settings.embedding_batch_size:
                if dry_run:
                    print(f"    [DRY RUN] Would embed {len(batch_docs)} chunks")
                else:
                    await _embed_and_upsert(batch_docs)

                total_ingested += len(batch_new_ids)
                append_checkpoint(source, batch_new_ids)

                elapsed = time.time() - start
                processed = total_skipped + total_ingested
                pct = processed / total_lines * 100 if total_lines else 0
                eta_min = ((total_lines - processed) / max(processed / max(elapsed, 1), 0.1)) / 60

                print(
                    f"    [{source}] {pct:.1f}% | {total_ingested:,} ingested "
                    f"({total_chunks:,} chunks) | {total_skipped:,} skipped | "
                    f"ETA: {eta_min:.0f}min"
                )

                save_progress(source, {
                    "ingested": total_ingested,
                    "chunks": total_chunks,
                    "skipped": total_skipped,
                    "total": total_lines,
                    "percent": round(pct, 1),
                    "elapsed_seconds": round(elapsed, 1),
                    "eta_minutes": round(eta_min, 1),
                    "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
                })

                batch_docs = []
                batch_new_ids = set()

    # Final batch
    if batch_docs:
        if not dry_run:
            await _embed_and_upsert(batch_docs)
        total_ingested += len(batch_new_ids)
        append_checkpoint(source, batch_new_ids)

    elapsed = time.time() - start
    stats = {
        "source": source,
        "ingested": total_ingested,
        "chunks": total_chunks,
        "skipped": total_skipped,
        "elapsed_seconds": round(elapsed, 1),
    }
    print(f"\n  {source} done: {json.dumps(stats)}")

    save_progress(source, {**stats, "status": "complete"})
    return stats


async def main(source: str | None, limit: int | None, dry_run: bool):
    settings.ensure_dirs()

    print(f"\nLITIGIA Embedding Ingestion Pipeline")
    print(f"Data: {settings.data_clean}")
    print(f"ChromaDB: {settings.data_root / 'chromadb'}")
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Current collection size: {collection_count():,} documents")
    if dry_run:
        print(f"MODE: DRY RUN")

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
    print(f"Collection size: {collection_count():,}")
    print(f"{'='*60}")


def show_status():
    print(f"\nLITIGIA Vector Store Status")
    print(f"ChromaDB path: {settings.data_root / 'chromadb'}")
    print(f"Collection: {settings.qdrant_collection}")
    print(f"Documents: {collection_count():,}")

    for progress_file in sorted(settings.data_logs.glob("*_ingest_progress.json")):
        data = json.loads(progress_file.read_text())
        print(f"\n  {progress_file.stem}:")
        for k, v in data.items():
            print(f"    {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LITIGIA Embedding Ingestion")
    parser.add_argument("--source", choices=["saij", "jurisgpt"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        asyncio.run(main(args.source, args.limit, args.dry_run))
