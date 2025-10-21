import os
import json
import datetime
import numpy as np
from pathlib import Path

# === CONFIG ===
DATA_DIR = Path(".")
LOG_FILE = DATA_DIR / "learning_log.md"
WEIGHTS_FILE = DATA_DIR / "learning_weights.json"
MEMORY_FILE = DATA_DIR / "adaptive_memory.json"

# === Helper: Safe JSON Loader ===
def load_json_safe(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default or {}

# === Load Inputs ===
print("[INFO] Loading input data for continuous learning...")

review_history = load_json_safe("review_history.json", {"reviews": []})
self_eval = load_json_safe("self_eval_metrics.json", {})
trend_data = load_json_safe("trend_report.json", {})
adaptive_log = load_json_safe("ai_adaptive_log.json", {})

print(f"[INFO] Loaded {len(review_history.get('reviews', []))} past reviews.")

# === Initialize weights ===
weights = {
    "clarity": 1.0,
    "depth": 1.0,
    "risk_awareness": 1.0,
    "consistency": 1.0,
    "actionability": 1.0,
    "confidence": 1.0
}

# === Load previous weights if exist ===
if WEIGHTS_FILE.exists():
    with open(WEIGHTS_FILE, "r") as f:
        prev_weights = json.load(f)
        weights.update(prev_weights)
        print("[INFO] Previous learning weights loaded.")

# === Step 1: Compute aggregate metrics ===
def compute_metric_average(key):
    values = [r.get(key, 0) for r in review_history.get("reviews", []) if isinstance(r.get(key, 0), (int, float))]
    return np.mean(values) if values else 0.0

avg_clarity = compute_metric_average("clarity")
avg_depth = compute_metric_average("depth")
avg_actionability = compute_metric_average("actionability")
avg_confidence = compute_metric_average("confidence")

# === Step 2: Adjust weights based on trends ===
print("[INFO] Adjusting weights based on aggregate PR trends...")

adjustments = {
    "clarity": np.clip(1 + (0.5 - avg_clarity) * 0.3, 0.8, 1.2),
    "depth": np.clip(1 + (0.5 - avg_depth) * 0.4, 0.8, 1.3),
    "actionability": np.clip(1 + (0.5 - avg_actionability) * 0.3, 0.8, 1.2),
    "confidence": np.clip(1 + (0.5 - avg_confidence) * 0.2, 0.8, 1.2),
}

for k, factor in adjustments.items():
    old_value = weights[k]
    weights[k] = round(old_value * factor, 3)

# === Step 3: Reinforce based on self-evaluation feedback ===
print("[INFO] Reinforcing with self-evaluation metrics...")

if self_eval:
    for k in ["ai_self_score", "clarity", "actionability", "cqi"]:
        if k in self_eval and isinstance(self_eval[k], (int, float)):
            delta = (self_eval[k] - 0.7) * 0.15
            if "clarity" in k:
                weights["clarity"] += delta
            elif "actionability" in k:
                weights["actionability"] += delta
            elif "cqi" in k:
                weights["consistency"] += delta
            elif "self_score" in k:
                weights["confidence"] += delta

# === Step 4: Normalize weights ===
for key in weights:
    weights[key] = float(np.clip(weights[key], 0.5, 1.5))

# === Step 5: Build adaptive memory snapshot ===
adaptive_memory = {
    "last_updated": datetime.datetime.utcnow().isoformat(),
    "recent_performance": {
        "avg_clarity": round(avg_clarity, 3),
        "avg_depth": round(avg_depth, 3),
        "avg_actionability": round(avg_actionability, 3),
        "avg_confidence": round(avg_confidence, 3),
    },
    "weights": weights,
    "insights": {
        "trend_highlights": trend_data.get("key_findings", []),
        "behavioral_adaptations": {
            "focus_areas": ["code clarity", "risk identification", "contextual analysis"],
            "bias_corrections": ["reduce redundancy", "increase precision", "improve cross-PR continuity"]
        }
    }
}

# === Step 6: Persist outputs ===
print("[INFO] Saving updated learning weights and memory...")
with open(WEIGHTS_FILE, "w") as f:
    json.dump(weights, f, indent=2)

with open(MEMORY_FILE, "w") as f:
    json.dump(adaptive_memory, f, indent=2)

# === Step 7: Write learning log ===
with open(LOG_FILE, "w") as f:
    f.write(f"#  AI Continuous Learning Log — {datetime.datetime.utcnow().isoformat()}\n\n")
    f.write("### Weight Adjustments\n")
    for k, v in weights.items():
        f.write(f"- **{k}** → {v}\n")
    f.write("\n### Trend Insights\n")
    for insight in adaptive_memory["insights"]["trend_highlights"]:
        f.write(f"- {insight}\n")
    f.write("\n### Behavioral Adaptations\n")
    for b in adaptive_memory["insights"]["behavioral_adaptations"]["bias_corrections"]:
        f.write(f"- {b}\n")
    f.write("\n Continuous learning update complete.\n")

print("[SUCCESS] Continuous learning update complete. Artifacts saved.")
