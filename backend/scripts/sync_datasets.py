"""Incremental sync for SAIJ dataset from HuggingFace.

Downloads only NEW documents since the last sync. Uses the existing checkpoint
to know where we left off, streams from that point forward.

The upstream dataset (marianbasti/jurisprudencia-Argentina-SAIJ) is updated daily
by a scraper that pulls from saij.gob.ar. New rows are appended at the end,
so we can resume from our last processed index.

Usage:
    python -m scripts.sync_datasets              # sync new documents
    python -m scripts.sync_datasets --dry-run    # check for new docs without downloading
    python -m scripts.sync_datasets --status     # show sync status
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from scripts.normalizers.saij import normalize_saij_row
from scripts.normalizers.schema import LitigiaDocument


SYNC_LOG_FILE = "sync_history.jsonl"


def _load_checkpoint(source: str) -> dict:
    """Load the last checkpoint for a source."""
    checkpoint_file = settings.data_logs / f"{source}_checkpoint.json"
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text())
    return {"processed": 0, "written": 0, "skipped": 0, "errors": 0}


def _save_checkpoint(source: str, data: dict) -> None:
    """Save checkpoint for a source."""
    data["last_update"] = datetime.now(timezone.utc).isoformat()
    checkpoint_file = settings.data_logs / f"{source}_checkpoint.json"
    checkpoint_file.write_text(json.dumps(data, indent=2))


def _append_sync_log(entry: dict) -> None:
    """Append an entry to the sync history log."""
    log_file = settings.data_logs / SYNC_LOG_FILE
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _get_remote_row_count() -> int | None:
    """Get the total row count from HuggingFace dataset info.

    Returns None if we can't determine it (will fall back to streaming).
    """
    try:
        from huggingface_hub import dataset_info
        info = dataset_info(settings.saij_dataset)
        if info.card_data and hasattr(info.card_data, "dataset_size"):
            return None  # dataset_size is bytes, not rows
        # Try to get row count from splits
        if info.card_data and info.card_data.get("dataset_info"):
            for split in info.card_data["dataset_info"].get("splits", []):
                if split.get("name") == "train":
                    return split.get("num_examples")
    except Exception:
        pass
    return None


def sync_saij(dry_run: bool = False) -> dict:
    """Sync only new SAIJ documents since last checkpoint.

    Returns a dict with sync stats.
    """
    settings.ensure_dirs()
    output = settings.data_clean / "saij.jsonl"
    checkpoint = _load_checkpoint("saij")
    last_processed = checkpoint["processed"]

    print(f"\n{'='*60}")
    print(f"SAIJ Incremental Sync")
    print(f"Dataset: {settings.saij_dataset}")
    print(f"Last checkpoint: {last_processed:,} rows processed")
    print(f"{'='*60}")

    # Stream the dataset — skip to where we left off
    ds = load_dataset(
        settings.saij_dataset,
        split="train",
        streaming=True,
    )

    start_time = time.time()
    new_processed = 0
    new_written = 0
    new_skipped = 0
    new_errors = 0
    found_new = False

    if dry_run:
        print("\n  [DRY RUN] Checking for new documents...")
        # Stream and count how many rows exist beyond our checkpoint
        for i, _row in enumerate(ds):
            if i < last_processed:
                if i % 50000 == 0 and i > 0:
                    print(f"  Skipping... {i:,}/{last_processed:,}")
                continue
            new_processed += 1
            if new_processed >= 10:
                # Just check if there are at least 10 new rows
                break

        if new_processed > 0:
            print(f"\n  Found at least {new_processed} new documents since last sync")
        else:
            print(f"\n  No new documents found — dataset unchanged")

        return {
            "dry_run": True,
            "last_checkpoint": last_processed,
            "new_rows_found": new_processed,
        }

    # Real sync — append new documents to the existing JSONL
    print(f"\n  Streaming to find new documents after row {last_processed:,}...")

    with open(output, "a", encoding="utf-8") as f:
        for i, row in enumerate(ds):
            # Skip already-processed rows
            if i < last_processed:
                if i % 50000 == 0 and i > 0:
                    elapsed = time.time() - start_time
                    print(f"  Skipping... {i:,}/{last_processed:,} ({elapsed:.0f}s)")
                continue

            if not found_new:
                skip_time = time.time() - start_time
                print(f"  Skip phase done in {skip_time:.1f}s — processing new documents...")
                found_new = True

            new_processed += 1

            try:
                doc = normalize_saij_row(row)
                if doc:
                    f.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")
                    new_written += 1
                else:
                    new_skipped += 1
            except Exception as e:
                new_errors += 1
                if new_errors <= 5:
                    print(f"  ERROR row {i}: {e}")

            if new_processed % 1000 == 0:
                elapsed = time.time() - start_time
                rate = new_processed / max(elapsed, 1)
                print(f"  [{new_processed:,} new] written={new_written:,} skipped={new_skipped:,} ({rate:.0f}/s)")

    elapsed = time.time() - start_time

    # Update checkpoint with cumulative totals
    total_processed = last_processed + new_processed
    _save_checkpoint("saij", {
        "processed": total_processed,
        "written": checkpoint["written"] + new_written,
        "skipped": checkpoint["skipped"] + new_skipped,
        "errors": checkpoint["errors"] + new_errors,
    })

    # Log this sync run
    sync_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "saij",
        "previous_total": last_processed,
        "new_total": total_processed,
        "new_processed": new_processed,
        "new_written": new_written,
        "new_skipped": new_skipped,
        "new_errors": new_errors,
        "elapsed_seconds": round(elapsed, 1),
    }
    _append_sync_log(sync_entry)

    print(f"\n  Sync complete:")
    print(f"    New documents processed: {new_processed:,}")
    print(f"    New documents written:   {new_written:,}")
    print(f"    Skipped (too short):     {new_skipped:,}")
    print(f"    Errors:                  {new_errors:,}")
    print(f"    Total in dataset:        {total_processed:,}")
    print(f"    Time:                    {elapsed:.1f}s")

    return sync_entry


def show_status() -> None:
    """Show current sync status and history."""
    print(f"\n{'='*60}")
    print(f"LITIGIA Sync Status")
    print(f"{'='*60}")

    checkpoint = _load_checkpoint("saij")
    print(f"\n  SAIJ checkpoint:")
    print(f"    Processed:  {checkpoint['processed']:,}")
    print(f"    Written:    {checkpoint.get('written', 0):,}")
    print(f"    Last sync:  {checkpoint.get('last_update', 'never')}")

    # Show sync history
    log_file = settings.data_logs / SYNC_LOG_FILE
    if log_file.exists():
        print(f"\n  Recent sync history:")
        lines = log_file.read_text().strip().split("\n")
        for line in lines[-10:]:  # last 10 syncs
            entry = json.loads(line)
            ts = entry["timestamp"][:19].replace("T", " ")
            new = entry.get("new_written", 0)
            print(f"    {ts} UTC — +{new:,} new documents")
    else:
        print(f"\n  No sync history yet")

    # Show JSONL file size
    output = settings.data_clean / "saij.jsonl"
    if output.exists():
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"\n  saij.jsonl: {size_mb:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="LITIGIA SAIJ Incremental Sync")
    parser.add_argument("--dry-run", action="store_true", help="Check for new docs without downloading")
    parser.add_argument("--status", action="store_true", help="Show sync status and history")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    result = sync_saij(dry_run=args.dry_run)

    if not args.dry_run and result.get("new_written", 0) > 0:
        print(f"\n  Next step: python -m scripts.ingest_embeddings --incremental")


if __name__ == "__main__":
    main()
