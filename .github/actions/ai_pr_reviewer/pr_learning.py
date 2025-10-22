"""
Functions to compute simple peer-learning adjustments:
- aggregate history
- compute per-category weights
- output adaptive_weights.json used by reviewer.py
"""

import json
from statistics import mean
from pathlib import Path

HISTORY_PATH = Path("review_history.json")
WEIGHTS_OUT = Path("adaptive_weights.json")

DEFAULT_WEIGHTS = {
    "security_bias": 1.0,
    "test_bias": 1.0,
    "style_bias": 1.0,
    "depth_multiplier": 1.0
}

def load_history():
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def compute_weights(entries):
    """
    Simple heuristic:
      - if many 'high_risk' entries recently => increase security_bias & depth_multiplier
      - if many 'test update' entries => increase test_bias
      - if many small changes => reduce depth_multiplier
    """
    last_n = entries[-50:] if entries else []
    if not last_n:
        return DEFAULT_WEIGHTS

    avg_score = mean([e.get("priority_score", 0) for e in last_n if isinstance(e.get("priority_score"), (int,float))] or [0])
    high_risk_frac = sum(1 for e in last_n if e.get("high_risk")) / max(1, len(last_n))
    category_counts = {}
    for e in last_n:
        cat = e.get("category", "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    w = DEFAULT_WEIGHTS.copy()
    # depth multiplier scales with avg_score
    w["depth_multiplier"] = 1.0 + (avg_score / 100.0)  # avg_score 0..100 -> depth 1.0..2.0
    # security bias scales with high_risk_frac
    w["security_bias"] = 1.0 + high_risk_frac * 2.0
    # test bias if many test updates
    test_fraction = category_counts.get("test update", 0) / max(1, len(last_n))
    w["test_bias"] = 1.0 + test_fraction * 3.0
    # style bias reduces if many large diffs (we leave constant for simplicity)
    return {k: round(v, 3) for k,v in w.items()}

def write_weights(weights):
    WEIGHTS_OUT.write_text(json.dumps(weights, indent=2), encoding="utf-8")
    print(f"[INFO] Wrote adaptive weights to {WEIGHTS_OUT}")

def run():
    history = load_history()
    w = compute_weights(history)
    write_weights(w)
    return w

if __name__ == "__main__":
    run()
