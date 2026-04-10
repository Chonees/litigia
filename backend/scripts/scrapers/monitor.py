"""Real-time dashboard for all PJN scraper VPS instances.

Usage:
    python -m scripts.scrapers.monitor          # auto-refresh every 30s
    python -m scripts.scrapers.monitor --once    # check once and exit
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SERVERS = [
    ("45.77.105.158", "pjn-0", "CABA (5-5)"),
    ("45.76.19.148", "pjn-1", "Buenos Aires (1-1)"),
    ("45.32.206.98", "pjn-2", "Cordoba+Mendoza"),
    ("45.32.163.1", "pjn-3", "Salta+Jujuy"),
    ("140.82.21.105", "pjn-4", "Corrientes+Chaco"),
    ("155.138.175.113", "pjn-5", "Chubut+EntreRios"),
    ("216.238.110.134", "pjn-6", "Formosa+LaPampa"),
    ("149.28.195.165", "pjn-7", "LaRioja+Misiones"),
    ("64.176.5.210", "pjn-8", "Neuquen+RioNegro"),
    ("80.240.28.129", "pjn-9", "SanJuan+Catamarca"),
]

SSH_CMD = [
    "ssh", "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
]


def check_server(ip: str) -> dict:
    """SSH into server and get scraper status."""
    cmd = SSH_CMD + [f"root@{ip}", """
COUNT=$(wc -l /data/clean/pjn_tribunales.jsonl 2>/dev/null | awk '{print $1}')
[ -z "$COUNT" ] && COUNT=0
ERRORS=$(grep -c 'err:' /data/logs/scraper.log 2>/dev/null || echo 0)
RUNNING=$(ps aux | grep 'scraper.py' | grep -v grep | wc -l)
LAST=$(tail -1 /data/logs/scraper.log 2>/dev/null || echo 'no log')
COST=$(grep -o '\\$[0-9.]*' /data/logs/scraper.log 2>/dev/null | tail -1 || echo '$0')
echo "$COUNT|$ERRORS|$RUNNING|$COST|$LAST"
"""]

    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=10,
        )
        output = result.stdout.decode("utf-8", errors="replace").strip()
        if "|" in output:
            parts = output.split("|", 4)
            return {
                "count": int(parts[0]) if parts[0].isdigit() else 0,
                "errors": int(parts[1]) if parts[1].isdigit() else 0,
                "running": int(parts[2]) if parts[2].isdigit() else 0,
                "cost": parts[3] if len(parts) > 3 else "?",
                "last_log": parts[4][:150] if len(parts) > 4 else "",
                "status": "OK",
            }
    except Exception as e:
        pass

    return {"count": 0, "errors": 0, "running": 0, "cost": "?", "last_log": "", "status": "OFFLINE"}


def display(once: bool = False):
    """Show dashboard."""
    while True:
        os.system("cls" if os.name == "nt" else "clear")

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{'=' * 80}")
        print(f"  PJN SCRAPER DASHBOARD — {now}")
        print(f"{'=' * 80}")
        print()
        print(f"  {'SERVER':<12} {'JURISDICCION':<22} {'DOCS':>7} {'ERR':>5} {'STATUS':>8} {'API COST':>10}")
        print(f"  {'-'*12} {'-'*22} {'-'*7} {'-'*5} {'-'*8} {'-'*10}")

        total_docs = 0
        total_errors = 0
        all_ok = True

        for ip, name, juris in SERVERS:
            info = check_server(ip)
            total_docs += info["count"]
            total_errors += info["errors"]

            if info["status"] == "OFFLINE":
                status = "OFFLINE"
                all_ok = False
            elif info["running"] == 0:
                status = "STOPPED"
                all_ok = False
            else:
                status = "RUNNING"

            print(f"  {name:<12} {juris:<22} {info['count']:>7,} {info['errors']:>5} {status:>8} {info['cost']:>10}")

        print(f"  {'-'*12} {'-'*22} {'-'*7} {'-'*5} {'-'*8}")
        print(f"  {'TOTAL':<12} {'':<22} {total_docs:>7,} {total_errors:>5}")
        print()

        # ETA calculation
        # ~57K/day based on 10 servers at ~5.7K each
        if total_docs > 0:
            remaining = 1_000_000 - total_docs
            rate_per_day = 57_000  # estimated
            eta_days = remaining / rate_per_day
            print(f"  Progress: {total_docs:,} / 1,000,000 ({total_docs * 100 / 1_000_000:.1f}%)")
            print(f"  ETA: ~{eta_days:.1f} days at ~57K/day")
        print()

        # Show last log of each server
        print(f"  LAST ACTIVITY:")
        for ip, name, juris in SERVERS:
            info = check_server(ip)
            if info["last_log"]:
                log_short = info["last_log"][:100]
                print(f"    {name}: {log_short}")

        print()

        if once:
            break

        print(f"  [Refreshing in 30s... Ctrl+C to stop]")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    display(once=args.once)
