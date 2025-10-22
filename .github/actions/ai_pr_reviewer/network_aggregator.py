import os
import json
from pathlib import Path
from statistics import mean
from datetime import datetime
import glob

ROOT = Path(".")
GLOBAL_DIR = ROOT / "global_knowledge"
GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_SUMMARY = GLOBAL_DIR / "global_summary.json"
GLOBAL_WEIGHTS = GLOBAL_DIR / "adaptive_network_weights.json"
NETWORK_LOG = GLOBAL_DIR / "network_log.md"

# Candidate artifact locations (local workspace + common download dirs)
SEARCH_PATTERNS = [
    "**/review_history.json",
    "**/self_eval_metrics.json",
    "**/learning_outputs/self_eval_metrics.json",
    "**/learning_outputs/improvement_plan.json",
    "**/adaptive_weights.json",
    "**/learning_weights.json",
    "**/reinforcement_report.md",
    "**/reward_matrix.json",
    "**/ai_adaptive_log.json",
]

def find_files(patterns):
    files = set()
    for pat in patterns:
        for p in glob.glob(pat, recursive=True):
            files.add(Path(p))
    return sorted(files)

def load_json_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def aggregate_metrics(filepaths):
    """
    Extract numeric/global metrics from known artifact types.
    Returns aggregated dictionary and list of repository summaries.
    """
    repo_summaries = []
    clarity_vals = []
    action_vals = []
    avg_priority_scores = []
    learning_indexes = []
    reinforcement_scores = []
    adaptive_weights_list = []

    for p in filepaths:
        data = load_json_safe(p)
        if not data:
            continue
        name = p.name.lower()

        # review_history.json may be list or dict
        if p.name == "review_history.json":
            entries = data if isinstance(data, list) else data.get("reviews", []) if isinstance(data, dict) else []
            # compute average priority if entries exist
            scores = [e.get("priority_score", 0) for e in entries if isinstance(e.get("priority_score", 0), (int,float))]
            repo_summaries.append({
                "source": str(p),
                "num_reviews": len(entries),
                "avg_priority": round(mean(scores),2) if scores else None
            })
            if scores:
                avg_priority_scores.append(mean(scores))
        elif p.name.endswith("self_eval_metrics.json"):
            # expect metrics dict produced by self_improvement or continuous_learning
            # keys: learning_index, clarity, actionability, avg_priority_score
            li = data.get("learning_index")
            c = data.get("clarity")
            a = data.get("actionability")
            ap = data.get("avg_priority_score")
            if li is not None: learning_indexes.append(li)
            if c is not None: clarity_vals.append(c)
            if a is not None: action_vals.append(a)
            if ap is not None: avg_priority_scores.append(ap)
            repo_summaries.append({"source": str(p), "metrics": {"learning_index": li, "clarity": c, "actionability": a, "avg_priority": ap}})
        elif p.name in ("adaptive_weights.json", "learning_weights.json", "adaptive_network_weights.json"):
            adaptive_weights_list.append(data)
            repo_summaries.append({"source": str(p), "weights": list(data.keys())})
        elif p.name == "reward_matrix.json":
            rs = data.get("overall_reward_score")
            if rs is not None:
                reinforcement_scores.append(rs)
            repo_summaries.append({"source": str(p), "reward_overall": rs})
        else:
            # fallback: try to detect numeric fields
            numeric_vals = {k:v for k,v in (data.items() if isinstance(data, dict) else []) if isinstance(v,(int,float))}
            repo_summaries.append({"source": str(p), "numeric_keys": list(numeric_vals.keys())})

    aggregated = {
        "avg_clarity": round(mean(clarity_vals),3) if clarity_vals else None,
        "avg_actionability": round(mean(action_vals),3) if action_vals else None,
        "avg_priority_score": round(mean(avg_priority_scores),3) if avg_priority_scores else None,
        "avg_learning_index": round(mean(learning_indexes),3) if learning_indexes else None,
        "avg_reinforcement_score": round(mean(reinforcement_scores),3) if reinforcement_scores else None,
        "num_sources": len(filepaths)
    }

    return aggregated, repo_summaries, adaptive_weights_list

def merge_weights(weights_list):
    """
    Merge multiple adaptive weight dicts into a single network weight vector.
    Simple approach: average numeric fields where available.
    """
    if not weights_list:
        # default baseline
        baseline = {
            "clarity": 1.0,
            "depth": 1.0,
            "risk_awareness": 1.0,
            "actionability": 1.0,
            "consistency": 1.0,
            "confidence": 1.0,
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        return baseline

    # collect numeric keys
    keys = set()
    for w in weights_list:
        keys.update(k for k in w.keys() if isinstance(w.get(k), (int,float)))

    merged = {}
    for k in keys:
        vals = [w[k] for w in weights_list if isinstance(w.get(k), (int,float))]
        if vals:
            merged[k] = round(mean(vals), 3)
    merged["last_updated"] = datetime.utcnow().isoformat() + "Z"
    return merged

def write_global_artifacts(summary, merged_weights, repo_summaries):
    # ensure folder exists
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "aggregated_metrics": summary,
        "sources": repo_summaries,
        "notes": ["Aggregated by network_aggregator.py"]
    }
    with GLOBAL_SUMMARY.open("w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)
    with GLOBAL_WEIGHTS.open("w", encoding="utf-8") as f:
        json.dump(merged_weights, f, indent=2)

    # network human log
    with NETWORK_LOG.open("w", encoding="utf-8") as f:
        f.write(f"# Network Aggregation Log\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\n")
        f.write("## Aggregated Metrics\n\n")
        for k,v in summary.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n## Sources Scanned\n\n")
        for s in repo_summaries:
            f.write(f"- {s}\n")
        f.write("\n## Merged Weights Snapshot\n\n")
        for k,v in merged_weights.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n✅ Aggregation complete.\n")

    print(f"[INFO] Wrote global summary to {GLOBAL_SUMMARY} and weights to {GLOBAL_WEIGHTS}")

def optional_push_to_endpoint(endpoint_url):
    """
    Optional: if a central endpoint exists, push summary/weights there.
    The workflow must set KNOWLEDGE_CORE_ENDPOINT env var if used.
    This is intentionally basic and optional; no secrets are added here.
    """
    try:
        import requests
    except Exception:
        print("[INFO] requests not available — skipping remote push.")
        return

    try:
        payload = {
            "summary_path": str(GLOBAL_SUMMARY),
            "weights_path": str(GLOBAL_WEIGHTS),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        resp = requests.post(endpoint_url, json=payload, timeout=15)
        if resp.ok:
            print("[INFO] Pushed aggregated knowledge to remote endpoint.")
        else:
            print(f"[WARN] Remote push failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[WARN] Exception during remote push: {e}")

def main():
    print("[START] Network Aggregator: searching for artifacts...")
    files = find_files(SEARCH_PATTERNS)
    print(f"[INFO] Found {len(files)} candidate artifact files.")

    aggregated, repo_summaries, adaptive_weights_list = aggregate_metrics(files)
    merged_weights = merge_weights(adaptive_weights_list)

    write_global_artifacts(aggregated, merged_weights, repo_summaries)

    # optional push
    endpoint = os.getenv("KNOWLEDGE_CORE_ENDPOINT")
    if endpoint:
        print(f"[INFO] KNOWLEDGE_CORE_ENDPOINT detected — attempting push to {endpoint}")
        optional_push_to_endpoint(endpoint)
    print("[SUCCESS] Network aggregation finished.")

if __name__ == "__main__":
    main()
