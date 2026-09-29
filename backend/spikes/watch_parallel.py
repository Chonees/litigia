"""Every INTERVAL: status of the VPS, collect + merge into the local catalog, audit the batch.

Prints one "WATCH" line per round (easy to monitor) and the full audit. Exits when every
VPS has stopped, after a final collect. Usage: python -u -m spikes.watch_parallel
"""

import contextlib
import io
import sys
import time

from scripts.scrapers import deploy_parallel as dp

INTERVAL = 600
DESDE, HASTA = "2025-09-27", "2026-09-27"


def audit() -> str:
    from spikes import audit_batch
    buf = io.StringIO()
    sys.argv = ["audit_batch", "--desde", DESDE, "--hasta", HASTA]
    with contextlib.redirect_stdout(buf):
        audit_batch.main()
    return buf.getvalue()


def main() -> None:
    while True:
        rows = dp.status()
        alive = sum(1 for r in rows if r.get("alive"))
        docs = sum(sum(r.get("status", {}).values()) for r in rows)
        anomalies = {}
        for r in rows:
            for k, v in r.get("anomalies", {}).items():
                anomalies[k] = anomalies.get(k, 0) + v
        merged = dp.collect()
        report = audit()
        head = [l for l in report.splitlines() if l.startswith(("==", "estado:", "motivos:", "  tramos terminados"))]
        print(f"WATCH vivas {alive}/10 · docs en VPS {docs} · merge {merged} · anomalías "
              f"{ {k: v for k, v in anomalies.items() if v} } · " + " | ".join(head), flush=True)
        print(report, flush=True)
        if alive == 0:
            print("WATCH DONE: todas las VPS terminaron", flush=True)
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
