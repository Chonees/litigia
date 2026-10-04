"""Run the PJN scraper on N Vultr VPS in parallel (one IP each), then merge their catalogs.

Each VPS gets one slice of the date range, the scripts/ package over SSH and a .env with
the keys read from backend/.env (never printed). Every VPS keeps its own catalog.db;
`collect` snapshots them, downloads them and merges them into the local catalog, which
re-applies the data contract and enrichment.

Usage (from backend/):
    python -m scripts.scrapers.deploy_parallel deploy --camara C_5=35635 --camara C_2=13088 --desde 2025-09-27 --hasta 2026-09-27 -n 20
    python -m scripts.scrapers.deploy_parallel status
    python -m scripts.scrapers.deploy_parallel update      # ship new code to running VPS, restart
    python -m scripts.scrapers.deploy_parallel collect     # download + merge (+ audit)
    python -m scripts.scrapers.deploy_parallel destroy
"""

import argparse
import io
import json
import sqlite3
import subprocess
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import httpx

from scripts.catalog import Catalog
from scripts.config import settings

VULTR = "https://api.vultr.com/v2"
PLAN = "vc2-1c-1gb"
OS_ID = 2284                    # Ubuntu 24.04 LTS x64
REGIONS = ["ewr", "ord", "dfw", "mia", "lax", "sao", "atl", "sjc", "scl", "fra"]
TAG = "litigia-pjn"
SSH_KEY_NAME = "litigia-deploy"
KEY = Path.home() / ".ssh" / "id_ed25519"
SSH_OPTS = ["-i", str(KEY), "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
STATE = settings.data_logs / "parallel_state.json"
REMOTE_DB_DIR = settings.data_root / "parallel"
DEPS = "httpx pymupdf anthropic pydantic-settings"

# Expected work per ruling relative to the rest: seguridad social splits heavy days by Sala and case year
WORK_FACTOR = {"C_5": 1.5}

DOC_FIELDS = ["url", "tribunal", "jurisdiccion", "fecha", "caratula", "expediente", "tipo_fallo", "texto"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# -- pure helpers ---------------------------------------------------------------------

def split_range(start: date, end: date, n: int) -> list[tuple[date, date]]:
    """n contiguous slices covering [start, end], sizes differing by at most one day."""
    days = (end - start).days + 1
    n = max(1, min(n, days))
    out, cursor = [], start
    for i in range(n):
        length = days // n + (1 if i < days % n else 0)
        out.append((cursor, cursor + timedelta(days=length - 1)))
        cursor += timedelta(days=length)
    return out


def allocate(volumes: dict[str, int], n: int, factor: dict[str, float] | None = None) -> dict[str, int]:
    """VPS per cámara, proportional to its expected work (volume × factor), at least one each."""
    factor = factor or {}
    work = {c: v * factor.get(c, 1.0) for c, v in volumes.items()}
    total = sum(work.values()) or 1
    spare = n - len(volumes)
    shares = {c: spare * w / total for c, w in work.items()}
    out = {c: 1 + int(s) for c, s in shares.items()}
    for c in sorted(shares, key=lambda c: shares[c] - int(shares[c]), reverse=True)[: n - sum(out.values())]:
        out[c] += 1                                             # largest remainders get the leftovers
    return out


def package_scripts() -> bytes:
    """scripts/ as tar.gz, without caches, secrets or local-only helpers."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(SCRIPTS_DIR.rglob("*")):
            rel = path.relative_to(SCRIPTS_DIR.parent)
            if path.is_dir() or "__pycache__" in rel.parts or path.suffix in (".pyc", ".ps1") or path.name == ".env":
                continue
            tar.add(path, arcname=rel.as_posix())
    return buf.getvalue()


MERGE_COMMIT_EVERY = 500      # short transactions: a scraper may be writing the same local catalog


def merge_catalog(remote_db: Path, local: Catalog) -> dict:
    """Bring a remote catalog into the local one (idempotent; safe to repeat every few minutes).

    Documents already stored with the same text, active and with their listing data, are skipped, so repeated
    collects stay fast. A local copy that is disabled or lacks that data (the old scraper stored PDFs without
    it) is merged, which completes and reactivates it.
    Listings and failures come too, so scripts/reconcile.py can account for every ruling;
    a failure is dropped once the ruling is stored with text on either side.
    """
    src = sqlite3.connect(f"file:{remote_db}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    stats = {"documents": 0, "new": 0, "searches": 0, "listings": 0, "failures": 0}
    known = dict(local.db.execute("SELECT source || '|' || source_id, text_hash FROM documents "
                                  "WHERE active=1 AND tribunal<>'' AND caratula<>''"))
    for k, row in enumerate(src.execute("SELECT * FROM documents"), 1):
        stats["documents"] += 1
        if known.get(f"{row['source']}|{row['source_id']}", None) == row["text_hash"] and row["text_hash"]:
            continue
        d = {c: row[c] for c in DOC_FIELDS}
        d.update(source=row["source"], source_id=row["source_id"], firmantes=json.loads(row["firmantes"] or "[]"))
        stats["new"] += not local.has(d["source"], d["source_id"])
        local.upsert(d, commit=False)
        if k % MERGE_COMMIT_EVERY == 0:
            local.db.commit()
    for s in src.execute("SELECT * FROM searches"):
        local.db.execute("INSERT OR REPLACE INTO searches VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(s))
        stats["searches"] += 1
    local.db.commit()
    tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "listings" in tables:
        rows = [tuple(r) for r in src.execute("SELECT source, key, source_id FROM listings")]
        local.db.executemany("INSERT OR IGNORE INTO listings VALUES (?, ?, ?)", rows)
        stats["listings"] = len(rows)
    if "failures" in tables:
        rows = [tuple(r) for r in src.execute(
            "SELECT source, source_id, url, key, reason, attempts, first_at, last_at FROM failures")]
        local.db.executemany("INSERT OR REPLACE INTO failures VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        stats["failures"] = len(rows)
    local.db.execute("DELETE FROM failures WHERE EXISTS (SELECT 1 FROM documents d WHERE d.source=failures.source "
                     "AND d.source_id=failures.source_id AND d.chars>0)")
    local.db.commit()
    src.close()
    return stats


# -- Vultr ------------------------------------------------------------------------------

def _api() -> httpx.Client:
    if not settings.vultr_api_key:
        raise SystemExit("VULTR_API_KEY is missing in backend/.env")
    return httpx.Client(base_url=VULTR, timeout=60,
                        headers={"Authorization": f"Bearer {settings.vultr_api_key}"})


def _ssh_key_id(api: httpx.Client) -> str:
    pub = (KEY.parent / (KEY.name + ".pub")).read_text().strip()
    for k in api.get("/ssh-keys", params={"per_page": 100}).json()["ssh_keys"]:
        if k["ssh_key"].split()[:2] == pub.split()[:2]:
            return k["id"]
    r = api.post("/ssh-keys", json={"name": SSH_KEY_NAME, "ssh_key": pub})
    r.raise_for_status()
    return r.json()["ssh_key"]["id"]


def _load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"instances": []}


def _save_state(state: dict) -> None:
    settings.ensure_dirs()
    STATE.write_text(json.dumps(state, indent=2))


# -- SSH --------------------------------------------------------------------------------

def ssh(ip: str, cmd: str, stdin: bytes | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", *SSH_OPTS, f"root@{ip}", cmd], input=stdin, capture_output=True, timeout=timeout)


def scp_get(ip: str, remote: str, local: Path) -> None:
    local.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["scp", *SSH_OPTS, f"root@{ip}:{remote}", str(local)], capture_output=True, timeout=900)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors="replace")[:300])


def _env_file() -> bytes:
    lines = [f"ANTHROPIC_API_KEY={settings.anthropic_api_key}", "DATA_ROOT=/data"]
    if settings.anthropic_workspace_id:
        lines.append(f"ANTHROPIC_WORKSPACE_ID={settings.anthropic_workspace_id}")
    return ("\n".join(lines) + "\n").encode()


SETUP = (
    "set -e; export DEBIAN_FRONTEND=noninteractive; "
    "apt-get -o DPkg::Lock::Timeout=600 update -qq; "
    "apt-get -o DPkg::Lock::Timeout=600 install -y -qq python3-venv >/dev/null; "
    "mkdir -p /opt/litigia/app /data/logs; "
    "[ -x /opt/litigia/venv/bin/python ] || python3 -m venv /opt/litigia/venv; "
    f"/opt/litigia/venv/bin/pip install -q {DEPS}"
)


def _provision(inst: dict, package: bytes, env: bytes, jur: str, camara: str, tipo: str) -> str:
    ip = inst["ip"]
    for _ in range(40):                              # wait for sshd
        if ssh(ip, "true", timeout=30).returncode == 0:
            break
        time.sleep(10)
    else:
        return "ssh never came up"
    r = ssh(ip, SETUP, timeout=1800)
    if r.returncode:
        return "setup failed: " + r.stderr.decode(errors="replace")[-300:]
    if ssh(ip, "tar -xz -C /opt/litigia/app", stdin=package).returncode:
        return "upload failed"
    if ssh(ip, "umask 077; cat > /opt/litigia/app/.env", stdin=env).returncode:
        return "env upload failed"
    return _start(inst, jur, camara, tipo)


# "[p]" keeps pgrep from matching the remote shell whose own command line contains the pattern
ALIVE = "pgrep -f '[p]jn_tribunales'"


def _start(inst: dict, jur: str, camara: str, tipo: str) -> str:
    ip = inst["ip"]
    run = (f"cd /opt/litigia/app && DATA_ROOT=/data PYTHONIOENCODING=utf-8 setsid nohup "
           f"/opt/litigia/venv/bin/python -u -m scripts.scrapers.pjn_tribunales --jurisdiccion {jur} "
           f"--camara {camara} --tipo {tipo} --desde {inst['desde']} --hasta {inst['hasta']} "
           f">> /data/logs/run.log 2>&1 < /dev/null &")
    try:
        ssh(ip, run, timeout=20)   # Git-for-Windows ssh can keep the channel open after `&`
    except subprocess.TimeoutExpired:
        pass
    alive = ssh(ip, ALIVE, timeout=30).returncode == 0
    return "running" if alive else "start failed"


def update(_args=None) -> None:
    """Ship the current scripts/ to every VPS that is still scraping and restart it.

    The scraper resumes from its own catalog: finished searches are skipped, known
    rulings are only refreshed. VPS that already finished are left alone.
    """
    state = _load_state()
    package = package_scripts()
    live = [i for i in state["instances"] if not i.get("destroyed") and i.get("ip")]

    def one(inst: dict) -> str:
        ip = inst["ip"]
        if ssh(ip, ALIVE, timeout=30).returncode != 0:
            return "finished, left alone"
        ssh(ip, "pkill -f pjn_tribunales; sleep 2", timeout=60)
        if ssh(ip, "rm -rf /opt/litigia/app/scripts && tar -xz -C /opt/litigia/app", stdin=package).returncode:
            return "upload failed"
        return _start(inst, state["jurisdiccion"], inst.get("camara", state["camara"]), state["tipo"])

    with ThreadPoolExecutor(max(1, len(live))) as pool:
        for inst, res in zip(live, pool.map(one, live)):
            log(f"{inst['label']:24} {res}")


def deploy(args) -> None:
    state = _load_state()
    if [i for i in state["instances"] if not i.get("destroyed")]:
        raise SystemExit(f"There is a live deployment in {STATE}. Run destroy first.")
    # --camara C_5=35635 (repeatable): VPS are shared out by each cámara's volume (the site's one-year total)
    volumes = {c.split("=")[0]: int(c.split("=")[1]) if "=" in c else 1 for c in args.camara}
    per_camara = allocate(volumes, args.n, factor=WORK_FACTOR)
    plan = [(c, s, e) for c, k in per_camara.items()
            for s, e in split_range(date.fromisoformat(args.desde), date.fromisoformat(args.hasta), k)]
    log("VPS por cámara: " + ", ".join(f"{c} {k}" for c, k in per_camara.items()))
    package, env = package_scripts(), _env_file()
    with _api() as api:
        key_id = _ssh_key_id(api)
        instances = []
        for k, (camara, s, e) in enumerate(plan):
            region = REGIONS[k % len(REGIONS)]
            label = f"litigia-pjn-{k}-{camara}-{region}".lower().replace("_", "")
            r = api.post("/instances", json={"region": region, "plan": PLAN, "os_id": OS_ID, "label": label,
                                             "hostname": label, "sshkey_id": [key_id], "tags": [TAG],
                                             "backups": "disabled"})
            if r.status_code not in (200, 201, 202):
                log(f"create {label} failed: {r.status_code} {r.text[:200]} · {camara} {s}..{e} NOT COVERED")
                continue
            instances.append({"id": r.json()["instance"]["id"], "label": label, "region": region, "camara": camara,
                              "desde": s.isoformat(), "hasta": e.isoformat(), "ip": ""})
            log(f"created {label} for {camara} {s}..{e}")
            time.sleep(1)
        state = {"created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "camara": ",".join(volumes),
                 "jurisdiccion": args.jurisdiccion, "tipo": args.tipo, "instances": instances}
        _save_state(state)
        log("waiting for IPs…")
        pending = {i["id"] for i in instances}
        while pending:
            for inst in instances:
                if inst["id"] in pending:
                    d = api.get(f"/instances/{inst['id']}").json()["instance"]
                    if d["status"] == "active" and d["main_ip"] not in ("", "0.0.0.0"):
                        inst["ip"] = d["main_ip"]
                        pending.discard(inst["id"])
            time.sleep(10)
        _save_state(state)
    log("provisioning over SSH (install + upload + start)…")
    with ThreadPoolExecutor(len(instances)) as pool:
        results = list(pool.map(lambda i: _provision(i, package, env, args.jurisdiccion, i["camara"], args.tipo),
                                instances))
    for inst, res in zip(instances, results):
        inst["provision"] = res
        log(f"{inst['label']:24} {inst['ip']:16} {inst['desde']}..{inst['hasta']}  {res}")
    _save_state(state)


STATUS_PY = r"""
import sqlite3, json, subprocess
out = {"alive": subprocess.run(["pgrep", "-f", "pjn_tribunales"], capture_output=True).returncode == 0}
try:
    db = sqlite3.connect("file:/data/catalog.db?mode=ro", uri=True)
    out["status"] = dict(db.execute("select status, count(*) from documents group by 1").fetchall())
    out["searches"] = db.execute("select count(*), coalesce(sum(total),0), coalesce(sum(fetched),0) from searches where split=0").fetchone()
except Exception as e:
    out["error"] = str(e)[:100]
try:
    text = open("/data/logs/run.log", encoding="utf-8", errors="replace").read()
    out["last"] = text.strip().splitlines()[-1][:160]
    out["anomalies"] = {k: text.count(k) for k in ("PDF failed", "captcha rejected", "expected results", "SKIP", "Traceback")}
except Exception:
    out["last"] = ""
print(json.dumps(out))
"""


def _status_one(inst: dict) -> dict:
    try:
        r = ssh(inst["ip"], "/opt/litigia/venv/bin/python -", stdin=STATUS_PY.encode(), timeout=60)
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}           # busy VPS: unknown, not stopped
    try:
        return json.loads(r.stdout.decode())
    except Exception:
        return {"error": r.stderr.decode(errors="replace")[:120]}


def status(_args=None) -> list[dict]:
    state = _load_state()
    live = [i for i in state["instances"] if not i.get("destroyed") and i.get("ip")]
    with ThreadPoolExecutor(max(1, len(live))) as pool:
        rows = list(pool.map(_status_one, live))
    total = 0
    for inst, s in zip(live, rows):
        n = sum(s.get("status", {}).values())
        total += n
        print(f"{inst['label']:24} {inst['desde']}..{inst['hasta']}  {'VIVO ' if s.get('alive') else 'PARADO'} "
              f"docs {n:5}  {s.get('status', s.get('error', ''))}  "
              f"{ {k: v for k, v in s.get('anomalies', {}).items() if v} or ''} | {s.get('last', '')[:80]}")
    print(f"TOTAL documentos en las VPS: {total}")
    return rows


SNAPSHOT_PY = ("import sqlite3; s=sqlite3.connect('/data/catalog.db'); d=sqlite3.connect('/data/snapshot.db'); "
               "s.backup(d); d.close(); s.close()")


def collect(_args=None) -> dict:
    state = _load_state()
    live = [i for i in state["instances"] if not i.get("destroyed") and i.get("ip")]
    local = Catalog(settings.data_root / "catalog.db")
    totals = {"documents": 0, "new": 0, "searches": 0, "listings": 0, "failures": 0}
    for inst in live:
        try:
            r = ssh(inst["ip"], f"/opt/litigia/venv/bin/python -c \"{SNAPSHOT_PY}\"", timeout=300)
            if r.returncode:
                raise RuntimeError(r.stderr.decode(errors="replace")[:200])
            dest = REMOTE_DB_DIR / f"{inst['label']}.db"
            scp_get(inst["ip"], "/data/snapshot.db", dest)
            s = merge_catalog(dest, local)
            for k in totals:
                totals[k] += s[k]
            log(f"{inst['label']:24} {s}")
        except Exception as e:
            log(f"{inst['label']:24} collect failed: {e}")
    local.close()
    log(f"merged: {totals}")
    return totals


def destroy(_args=None) -> None:
    state = _load_state()
    with _api() as api:
        ids = {i["id"] for i in state["instances"] if not i.get("destroyed")}
        ids |= {i["id"] for i in api.get("/instances", params={"tag": TAG, "per_page": 100}).json()["instances"]}
        for iid in ids:
            r = api.delete(f"/instances/{iid}")
            log(f"destroy {iid}: {r.status_code}")
    for i in state["instances"]:
        i["destroyed"] = True
    _save_state(state)


def main() -> None:
    p = argparse.ArgumentParser(description="PJN scraper on parallel Vultr VPS")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deploy")
    d.add_argument("--jurisdiccion", default="5-5")
    d.add_argument("--camara", action="append", required=True, help="C_5=35635 (cámara=one-year volume), repeatable")
    d.add_argument("--tipo", default="D")
    d.add_argument("--desde", required=True)
    d.add_argument("--hasta", required=True)
    d.add_argument("-n", type=int, default=10)
    sub.add_parser("status")
    sub.add_parser("update")
    sub.add_parser("collect")
    sub.add_parser("destroy")
    args = p.parse_args()
    {"deploy": deploy, "status": status, "collect": collect, "destroy": destroy, "update": update}[args.cmd](args)


if __name__ == "__main__":
    main()
