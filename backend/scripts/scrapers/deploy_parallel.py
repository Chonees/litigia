"""Deploy PJN scraper to 10 Vultr VPS instances in parallel.

Each VPS scrapes ~2 jurisdictions with its own IP.
Total: ~500K sentencias in ~5 hours. Cost: ~$0.50 Vultr + ~$1.50 Haiku captchas.

Usage:
    python -m scripts.scrapers.deploy_parallel --deploy     # create 10 VPS + start scraping
    python -m scripts.scrapers.deploy_parallel --status     # check progress on all VPS
    python -m scripts.scrapers.deploy_parallel --collect    # download results from all VPS
    python -m scripts.scrapers.deploy_parallel --destroy    # destroy all VPS
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

VULTR_API_KEY = "77J53Q2Q2UKGDRJO2JQPKPQXWAJUXHMWBANQ"
VULTR_API = "https://api.vultr.com/v2"
PLAN = "vc2-1c-1gb"  # $5/mo = $0.007/h
OS_ID = 2284  # Ubuntu 24.04 LTS x64

# 10 regions for 10 different IPs
REGIONS = ["ewr", "ord", "dfw", "mia", "lax", "sao", "atl", "sjc", "scl", "fra"]

# 18 jurisdictions split across 10 servers
JURISDICTION_SPLITS = [
    ["5-5"],                          # CABA (biggest)
    ["1-1"],                          # Buenos Aires (second biggest)
    ["6-6", "13-13"],                 # Cordoba + Mendoza
    ["17-17", "17-10"],               # Salta + Jujuy
    ["7-7", "3-3"],                   # Corrientes + Chaco
    ["4-4", "8-8"],                   # Chubut + Entre Rios
    ["3-9", "1-11"],                  # Formosa + La Pampa
    ["6-12", "14-14"],                # La Rioja + Misiones
    ["16-15", "16-16"],               # Neuquen + Rio Negro
    ["13-18", "24-2"],                # San Juan + Catamarca
]

STATE_FILE = Path("D:/litigia-data/logs/parallel_deploy_state.json")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.core.config import settings


def _headers():
    return {"Authorization": f"Bearer {VULTR_API_KEY}", "Content-Type": "application/json"}


def _cloud_init(anthropic_key: str, jurisdictions: list[str], server_id: int) -> str:
    """Generate cloud-init script that installs deps and runs the scraper."""
    jur_args = " ".join(jurisdictions)
    return f"""#!/bin/bash
set -e

# Log everything
exec > /var/log/scraper-setup.log 2>&1

echo "=== [{server_id}] Setting up PJN scraper ==="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git

# Create workspace
mkdir -p /opt/scraper /data/clean /data/logs
cd /opt/scraper

# Install Python deps
python3 -m venv venv
source venv/bin/activate
pip install -q httpx pymupdf anthropic pydantic-settings

# Write the scraper files
cat > config_minimal.py << 'PYEOF'
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {{"env_file": ".env", "env_file_encoding": "utf-8"}}
    anthropic_api_key: str = ""
    data_root: Path = Path("/data")
    data_clean: Path = Path("/data/clean")
    data_logs: Path = Path("/data/logs")
    collection_name: str = "jurisprudencia"
    embedding_model: str = "BAAI/bge-m3"
    chunk_max_chars: int = 4000

settings = Settings()
PYEOF

cat > schema_minimal.py << 'PYEOF'
from dataclasses import dataclass, field, asdict

@dataclass
class LitigiaDocument:
    id: str = ""
    source: str = ""
    source_id: str = ""
    texto: str = ""
    sumario: str = ""
    caratula: str = ""
    tipo_documento: str = ""
    tipo_fallo: str = ""
    tribunal: str = ""
    tipo_tribunal: str = ""
    sala: str = ""
    magistrados: list = field(default_factory=list)
    materia: str = ""
    voces: list = field(default_factory=list)
    descriptores: list = field(default_factory=list)
    fecha: str = ""
    jurisdiccion: str = ""
    provincia: str = ""
    localidad: str = ""
    actor: str = ""
    demandado: str = ""
    sobre: str = ""
    referencias_normativas: list = field(default_factory=list)
    citas_jurisprudenciales: list = field(default_factory=list)
    texto_embedding: str = ""
    chunk_index: int = 0
    total_chunks: int = 1

    def to_dict(self):
        return asdict(self)
PYEOF

# Write .env
echo "ANTHROPIC_API_KEY={anthropic_key}" > .env

# Write run script for each jurisdiction
cat > run.sh << 'RUNEOF'
#!/bin/bash
source /opt/scraper/venv/bin/activate
cd /opt/scraper

for JUR in {jur_args}; do
    echo "=== Starting jurisdiction $JUR ==="
    python3 scraper.py --jurisdiccion "$JUR" --limit 100000 >> /data/logs/scraper_$JUR.log 2>&1 &
done

wait
echo "=== ALL DONE ==="
RUNEOF
chmod +x run.sh

# Download the actual scraper from the repo or write it inline
# For now, we fetch it from the machine via a simplified version
cat > scraper.py << 'SCRAPEREOF'
{scraper_code}
SCRAPEREOF

# Start scraping
nohup /opt/scraper/run.sh > /data/logs/run.log 2>&1 &

echo "=== Setup complete, scraper running ==="
"""


def get_scraper_code() -> str:
    """Read the scraper and adapt imports for the VPS minimal environment."""
    scraper_path = Path(__file__).parent / "pjn_tribunales.py"
    code = scraper_path.read_text(encoding="utf-8")

    # Replace imports to use minimal versions
    code = code.replace(
        "from app.core.config import settings",
        "from config_minimal import settings",
    )
    code = code.replace(
        "from scripts.normalizers.schema import LitigiaDocument",
        "from schema_minimal import LitigiaDocument",
    )

    return code


def deploy():
    """Create 10 VPS instances and start scraping."""
    scraper_code = get_scraper_code()
    # Escape for bash heredoc
    scraper_code_escaped = scraper_code.replace("\\", "\\\\").replace("$", "\\$").replace("`", "\\`")

    instances = []
    client = httpx.Client(headers=_headers(), timeout=30.0)

    for i, (region, jurisdictions) in enumerate(zip(REGIONS, JURISDICTION_SPLITS)):
        label = f"pjn-scraper-{i}-{region}"
        jur_str = "+".join(jurisdictions)

        print(f"  [{i+1}/10] Creating {label} in {region} for {jur_str}...")

        init_script = _cloud_init(
            settings.anthropic_api_key,
            jurisdictions,
            i,
        )
        # Replace the scraper code placeholder
        init_script = init_script.replace("{scraper_code}", scraper_code_escaped)

        import base64
        user_data = base64.b64encode(init_script.encode()).decode()

        r = client.post(f"{VULTR_API}/instances", json={
            "region": region,
            "plan": PLAN,
            "os_id": OS_ID,
            "label": label,
            "hostname": label,
            "user_data": user_data,
            "backups": "disabled",
            "tags": ["pjn-scraper"],
        })

        if r.status_code in (200, 201, 202):
            data = r.json()["instance"]
            instances.append({
                "id": data["id"],
                "label": label,
                "region": region,
                "jurisdictions": jurisdictions,
                "ip": data.get("main_ip", "pending"),
                "status": data.get("status", "pending"),
            })
            print(f"    Created: {data['id']} (IP: {data.get('main_ip', 'pending')})")
        else:
            print(f"    ERROR: {r.status_code} {r.text[:200]}")

        time.sleep(2)  # Don't hit Vultr API too fast

    # Save state
    STATE_FILE.write_text(json.dumps({"instances": instances, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2))
    print(f"\n  {len(instances)} instances created. State saved to {STATE_FILE}")
    print(f"  Wait ~3-5 minutes for setup, then check with --status")

    client.close()


def status():
    """Check status of all VPS instances."""
    if not STATE_FILE.exists():
        print("No deployment found. Run --deploy first.")
        return

    state = json.loads(STATE_FILE.read_text())
    client = httpx.Client(headers=_headers(), timeout=30.0)

    print(f"  Deployed at: {state['created_at']}\n")

    for inst in state["instances"]:
        # Get current status from Vultr
        r = client.get(f"{VULTR_API}/instances/{inst['id']}")
        if r.status_code == 200:
            data = r.json()["instance"]
            ip = data.get("main_ip", "?")
            status = data.get("status", "?")
            power = data.get("power_status", "?")
            print(f"  {inst['label']:30s} | {ip:16s} | {status:10s} | {power:8s} | {inst['jurisdictions']}")

            # If running, try to check scraper progress via SSH/logs
            if ip and ip != "0.0.0.0" and status == "active":
                pass  # Could SSH to check /data/logs/ but needs SSH key setup
        else:
            print(f"  {inst['label']:30s} | ERROR: {r.status_code}")

    client.close()
    print(f"\n  To check logs on a server: ssh root@<IP> 'cat /data/logs/run.log'")
    print(f"  To check scraper output: ssh root@<IP> 'wc -l /data/clean/pjn_tribunales.jsonl'")


def collect():
    """Download results from all VPS instances."""
    if not STATE_FILE.exists():
        print("No deployment found.")
        return

    import subprocess

    state = json.loads(STATE_FILE.read_text())
    output_dir = Path("D:/litigia-data/clean/parallel_results")
    output_dir.mkdir(exist_ok=True)

    for inst in state["instances"]:
        ip = inst.get("ip", "")
        if not ip or ip == "0.0.0.0":
            # Get updated IP
            r = httpx.get(f"{VULTR_API}/instances/{inst['id']}", headers=_headers())
            if r.status_code == 200:
                ip = r.json()["instance"].get("main_ip", "")

        if ip and ip != "0.0.0.0":
            label = inst["label"]
            print(f"  Downloading from {label} ({ip})...")
            dest = output_dir / f"{label}.jsonl"
            result = subprocess.run(
                ["scp", "-o", "StrictHostKeyChecking=no",
                 f"root@{ip}:/data/clean/pjn_tribunales.jsonl",
                 str(dest)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                lines = sum(1 for _ in open(dest, encoding="utf-8"))
                size = dest.stat().st_size / (1024 * 1024)
                print(f"    OK: {lines:,} sentencias, {size:.1f}MB")
            else:
                print(f"    ERROR: {result.stderr[:200]}")

    # Merge all files
    merged = output_dir.parent / "pjn_tribunales.jsonl"
    seen_ids = set()
    total = 0

    # Keep existing if any
    if merged.exists():
        with open(merged, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    sid = json.loads(line.strip()).get("source_id", "")
                    if sid:
                        seen_ids.add(sid)
                        total += 1
                except Exception:
                    pass

    with open(merged, "a", encoding="utf-8") as out:
        for jsonl in sorted(output_dir.glob("*.jsonl")):
            with open(jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        doc = json.loads(line.strip())
                        sid = doc.get("source_id", "")
                        if sid and sid not in seen_ids:
                            out.write(line.strip() + "\n")
                            seen_ids.add(sid)
                            total += 1
                    except Exception:
                        pass

    print(f"\n  Merged: {total:,} unique sentencias in {merged}")


def destroy():
    """Destroy all VPS instances."""
    if not STATE_FILE.exists():
        print("No deployment found.")
        return

    state = json.loads(STATE_FILE.read_text())
    client = httpx.Client(headers=_headers(), timeout=30.0)

    for inst in state["instances"]:
        print(f"  Destroying {inst['label']}...")
        r = client.delete(f"{VULTR_API}/instances/{inst['id']}")
        if r.status_code in (200, 204):
            print(f"    OK")
        else:
            print(f"    {r.status_code}: {r.text[:100]}")

    STATE_FILE.unlink(missing_ok=True)
    print(f"\n  All instances destroyed.")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--destroy", action="store_true")
    args = parser.parse_args()

    if args.deploy:
        deploy()
    elif args.status:
        status()
    elif args.collect:
        collect()
    elif args.destroy:
        destroy()
    else:
        print("Use --deploy, --status, --collect, or --destroy")
