"""Download, normalize, and store legal datasets from HuggingFace.

Writes cleaned JSONL to D:/litigia-data/clean/ — one file per source.
Supports resume: if interrupted, re-run and it picks up from the last checkpoint.

Usage:
    python -m scripts.download_datasets                    # both datasets
    python -m scripts.download_datasets --source saij      # only SAIJ
    python -m scripts.download_datasets --source jurisgpt  # only JurisGPT
    python -m scripts.download_datasets --limit 5000       # cap documents
    python -m scripts.download_datasets --stats            # show stats only
"""

import argparse
import json
import sys
import time
from pathlib import Path

from datasets import load_dataset

# Add parent to path so normalizers are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from scripts.normalizers.saij import normalize_saij_row
from scripts.normalizers.jurisgpt import normalize_jurisgpt_row
from scripts.normalizers.schema import LitigiaDocument


class ProgressTracker:
    """Track download progress with checkpoint support."""

    def __init__(self, source: str, log_dir: Path):
        self.source = source
        self.checkpoint_file = log_dir / f"{source}_checkpoint.json"
        self.stats_file = log_dir / f"{source}_stats.json"
        self.processed = 0
        self.written = 0
        self.skipped = 0
        self.errors = 0
        self.start_time = time.time()
        self._load_checkpoint()

    def _load_checkpoint(self) -> None:
        if self.checkpoint_file.exists():
            data = json.loads(self.checkpoint_file.read_text())
            self.processed = data.get("processed", 0)
            self.written = data.get("written", 0)
            self.skipped = data.get("skipped", 0)
            self.errors = data.get("errors", 0)
            print(f"  Resuming from checkpoint: {self.processed} processed, {self.written} written")

    def save_checkpoint(self) -> None:
        self.checkpoint_file.write_text(json.dumps({
            "processed": self.processed,
            "written": self.written,
            "skipped": self.skipped,
            "errors": self.errors,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, indent=2))

    def save_stats(self) -> None:
        elapsed = time.time() - self.start_time
        stats = {
            "source": self.source,
            "total_processed": self.processed,
            "total_written": self.written,
            "total_skipped": self.skipped,
            "total_errors": self.errors,
            "elapsed_seconds": round(elapsed, 1),
            "docs_per_second": round(self.processed / max(elapsed, 1), 1),
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.stats_file.write_text(json.dumps(stats, indent=2))
        return stats

    def log_progress(self, interval: int = 5000) -> None:
        if self.processed % interval == 0 and self.processed > 0:
            elapsed = time.time() - self.start_time
            rate = self.processed / max(elapsed, 1)
            print(
                f"  [{self.source}] {self.processed:,} processed | "
                f"{self.written:,} written | {self.skipped:,} skipped | "
                f"{rate:.0f} docs/s"
            )
            self.save_checkpoint()


def _write_doc(f, doc: LitigiaDocument) -> None:
    """Write a single document to JSONL file."""
    f.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")


def download_saij(limit: int | None = None) -> dict:
    """Download and normalize SAIJ dataset with streaming."""
    settings.ensure_dirs()
    output = settings.data_clean / "saij.jsonl"
    tracker = ProgressTracker("saij", settings.data_logs)

    print(f"\n{'='*60}")
    print(f"SAIJ — marianbasti/jurisprudencia-Argentina-SAIJ")
    print(f"Output: {output}")
    print(f"Streaming mode (720GB+ dataset)")
    print(f"{'='*60}")

    # Stream to avoid loading 720GB into memory
    ds = load_dataset(
        settings.saij_dataset,
        split="train",
        streaming=True,
        trust_remote_code=True,
    )

    # If resuming, we need to skip already-processed rows
    skip_count = tracker.processed

    mode = "a" if skip_count > 0 else "w"
    with open(output, mode, encoding="utf-8") as f:
        for i, row in enumerate(ds):
            # Skip already-processed rows on resume
            if i < skip_count:
                continue

            tracker.processed += 1

            if limit and tracker.written >= limit:
                print(f"  Limit reached: {limit} documents")
                break

            try:
                doc = normalize_saij_row(row)
                if doc:
                    _write_doc(f, doc)
                    tracker.written += 1
                else:
                    tracker.skipped += 1
            except Exception as e:
                tracker.errors += 1
                if tracker.errors <= 10:
                    print(f"  ERROR row {i}: {e}")
                elif tracker.errors == 11:
                    print("  (suppressing further error messages)")

            tracker.log_progress(interval=10000)

    stats = tracker.save_stats()
    tracker.save_checkpoint()
    print(f"\n  SAIJ done: {stats}")
    return stats


def download_jurisgpt(limit: int | None = None) -> dict:
    """Download and normalize JurisGPT dataset."""
    settings.ensure_dirs()
    output = settings.data_clean / "jurisgpt.jsonl"
    tracker = ProgressTracker("jurisgpt", settings.data_logs)

    print(f"\n{'='*60}")
    print(f"JurisGPT — harpomaxx/jurisgpt")
    print(f"Output: {output}")
    print(f"{'='*60}")

    # Small dataset, no need for streaming
    ds = load_dataset(settings.jurisgpt_dataset, split="train")
    print(f"  Loaded {len(ds)} rows")

    with open(output, "w", encoding="utf-8") as f:
        for row in ds:
            tracker.processed += 1

            if limit and tracker.written >= limit:
                break

            try:
                doc = normalize_jurisgpt_row(row)
                if doc:
                    _write_doc(f, doc)
                    tracker.written += 1
                else:
                    tracker.skipped += 1
            except Exception as e:
                tracker.errors += 1
                print(f"  ERROR: {e}")

    stats = tracker.save_stats()
    print(f"\n  JurisGPT done: {stats}")
    return stats


def show_stats() -> None:
    """Display stats from previous runs."""
    print(f"\n{'='*60}")
    print(f"LITIGIA Data Pipeline — Statistics")
    print(f"Data directory: {settings.data_root}")
    print(f"{'='*60}")

    for stats_file in sorted(settings.data_logs.glob("*_stats.json")):
        stats = json.loads(stats_file.read_text())
        print(f"\n  {stats['source'].upper()}:")
        print(f"    Processed:  {stats['total_processed']:,}")
        print(f"    Written:    {stats['total_written']:,}")
        print(f"    Skipped:    {stats['total_skipped']:,}")
        print(f"    Errors:     {stats['total_errors']:,}")
        print(f"    Speed:      {stats['docs_per_second']} docs/s")
        print(f"    Completed:  {stats['completed_at']}")

    # Show file sizes
    print(f"\n  Files:")
    for jsonl in sorted(settings.data_clean.glob("*.jsonl")):
        size_mb = jsonl.stat().st_size / (1024 * 1024)
        lines = sum(1 for _ in open(jsonl, encoding="utf-8"))
        print(f"    {jsonl.name}: {size_mb:.1f} MB, {lines:,} documents")


def main():
    parser = argparse.ArgumentParser(description="LITIGIA Data Pipeline")
    parser.add_argument("--source", choices=["saij", "jurisgpt"], help="Download only this source")
    parser.add_argument("--limit", type=int, help="Max documents per source")
    parser.add_argument("--stats", action="store_true", help="Show stats from previous runs")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print(f"\nLITIGIA Data Pipeline")
    print(f"Data directory: {settings.data_root}")

    if args.source != "jurisgpt":
        download_saij(limit=args.limit)

    if args.source != "saij":
        download_jurisgpt(limit=args.limit)

    print(f"\n{'='*60}")
    print(f"Pipeline complete. Run 'python -m scripts.download_datasets --stats' for details.")
    print(f"Next step: python -m scripts.ingest_embeddings")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
