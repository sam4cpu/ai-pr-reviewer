import os
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(".")
GLOBAL_DIR = ROOT / "global_knowledge"
SUMMARY = GLOBAL_DIR / "global_summary.json"
WEIGHTS = GLOBAL_DIR / "adaptive_network_weights.json"
LOG = GLOBAL_DIR / "network_log.md"

DEFAULT_SUMMARY = {
    "generated_at": None,
    "repositories": [],
    "num_repos": 0,
    "metrics_aggregated": {},
    "notes": ["Initialized global knowledge core - no data yet."]
}

DEFAULT_WEIGHTS = {
    "clarity": 1.0,
    "depth": 1.0,
    "risk_awareness": 1.0,
    "actionability": 1.0,
    "consistency": 1.0,
    "confidence": 1.0,
    "last_updated": None
}

def safe_write(path: Path, obj):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Wrote {path}")
    except Exception as e:
        print(f"[WARN] Failed to write {path}: {e}")

def init_global_knowledge():
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    if not SUMMARY.exists():
        DEFAULT_SUMMARY["generated_at"] = datetime.utcnow().isoformat() + "Z"
        safe_write(SUMMARY, DEFAULT_SUMMARY)
    if not WEIGHTS.exists():
        DEFAULT_WEIGHTS["last_updated"] = datetime.utcnow().isoformat() + "Z"
        safe_write(WEIGHTS, DEFAULT_WEIGHTS)
    if not LOG.exists():
        with LOG.open("w", encoding="utf-8") as f:
            f.write(f"# Network Knowledge Core\n\nInitialized at {datetime.utcnow().isoformat()}Z\n\n")
        print(f"[INFO] Created log at {LOG}")

def load_state():
    summary = {}
    weights = {}
    try:
        with SUMMARY.open("r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception:
        summary = DEFAULT_SUMMARY
    try:
        with WEIGHTS.open("r", encoding="utf-8") as f:
            weights = json.load(f)
    except Exception:
        weights = DEFAULT_WEIGHTS
    return summary, weights

def append_log(entry: str):
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()}Z — {entry}\n")
    except Exception as e:
        print(f"[WARN] Failed to append to log: {e}")

def main():
    print("[START] Initializing Network Knowledge Core...")
    init_global_knowledge()
    summary, weights = load_state()
    append_log("Global knowledge core initialized or verified.")
    print("[SUCCESS] Network Knowledge Core ready.")
    print(f"[INFO] Summary path: {SUMMARY}")
    print(f"[INFO] Weights path: {WEIGHTS}")

if __name__ == "__main__":
    main()
