#!/usr/bin/env bash
# LITIGIA Daily SAIJ Sync
#
# Downloads new documents from HuggingFace (SAIJ dataset updates daily).
# Designed to run as a cron job or Windows Task Scheduler task.
#
# Setup (Linux/Mac cron):
#   crontab -e
#   0 6 * * * /path/to/litigia/backend/scripts/sync.sh >> /path/to/litigia-data/logs/sync_cron.log 2>&1
#
# Setup (Windows Task Scheduler):
#   schtasks /create /tn "LITIGIA-Sync" /tr "bash /c/Users/lucas/OneDrive/Escritorio/LITIGIA/backend/scripts/sync.sh" /sc daily /st 06:00
#
# Or manually:
#   bash backend/scripts/sync.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="D:/litigia-data/logs"

mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
echo ""
echo "=========================================="
echo "LITIGIA Sync — $TIMESTAMP"
echo "=========================================="

cd "$BACKEND_DIR"

# Activate venv if it exists
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run incremental sync
python -m scripts.sync_datasets

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "Sync completed successfully at $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
else
    echo ""
    echo "ERROR: Sync failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
