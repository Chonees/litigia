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

    def __init__(self, source: str, log_dir: Path, total: int | None = None):
        self.source = source
        self.total = total
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
        data = {
            "processed": self.processed,
            "written": self.written,
            "skipped": self.skipped,
            "errors": self.errors,
            "total": self.total,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if self.total:
            data["percent"] = round(self.processed / self.total * 100, 1)
        self.checkpoint_file.write_text(json.dumps(data, indent=2))

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
            pct = f" ({self.processed / self.total * 100:.1f}%)" if self.total else ""
            eta = ""
            if self.total and rate > 0:
                remaining = (self.total - self.processed) / rate
                eta = f" | ETA: {remaining / 60:.0f}min"
            print(
                f"  [{self.source}] {self.processed:,}{pct} | "
                f"{self.written:,} written | {self.skipped:,} skipped | "
                f"{rate:.0f} docs/s{eta}"
            )
            self.save_checkpoint()


def _write_doc(f, doc: LitigiaDocument) -> None:
    """Write a single document to JSONL file."""
    f.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")


def _find_saij_raw() -> Path | None:
    """Find the raw SAIJ JSONL file (downloaded via huggingface_hub)."""
    # Direct download location
    direct = settings.data_raw / "dataset.jsonl"
    if direct.exists():
        return direct

    # huggingface_hub cache — search for the file
    for f in settings.data_raw.rglob("dataset.jsonl"):
        return f

    return None


def download_saij(limit: int | None = None) -> dict:
    """Download and normalize SAIJ dataset.

    Strategy:
    1. If raw JSONL already exists in D:/litigia-data/raw/ → read it directly
    2. Otherwise → download via huggingface_hub, then read
    """
    settings.ensure_dirs()
    output = settings.data_clean / "saij.jsonl"

    print(f"\n{'='*60}")
    print(f"SAIJ — marianbasti/jurisprudencia-Argentina-SAIJ")
    print(f"Output: {output}")
    print(f"{'='*60}")

    # Step 1: Find or download the raw JSONL
    raw_file = _find_saij_raw()

    if raw_file:
        print(f"  Found raw JSONL: {raw_file} ({raw_file.stat().st_size / (1024*1024):.0f} MB)")
    else:
        print(f"  Downloading raw JSONL via huggingface_hub...")
        from huggingface_hub import hf_hub_download
        raw_file = Path(hf_hub_download(
            settings.saij_dataset,
            "dataset.jsonl",
            repo_type="dataset",
            cache_dir=str(settings.data_raw),
        ))
        print(f"  Downloaded: {raw_file} ({raw_file.stat().st_size / (1024*1024):.0f} MB)")

    # Step 2: Count total lines for progress percentage
    print(f"  Counting total documents...")
    total_lines = sum(1 for _ in open(raw_file, encoding="utf-8"))
    print(f"  Total rows in SAIJ: {total_lines:,}")

    tracker = ProgressTracker("saij", settings.data_logs, total=total_lines)

    # Step 3: Process — skip already-processed rows on resume
    skip_count = tracker.processed

    mode = "a" if skip_count > 0 else "w"
    with open(output, mode, encoding="utf-8") as f_out:
        with open(raw_file, "r", encoding="utf-8") as f_in:
            for i, line in enumerate(f_in):
                if i < skip_count:
                    continue

                tracker.processed += 1

                if limit and tracker.written >= limit:
                    print(f"  Limit reached: {limit} documents")
                    break

                try:
                    row = json.loads(line)
                    doc = normalize_saij_row(row)
                    if doc:
                        _write_doc(f_out, doc)
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
