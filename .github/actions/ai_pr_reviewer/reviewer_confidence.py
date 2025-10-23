"""
reviewer_confidence.py
- Reads review_history.json (list of past review entries with priority_score, high_risk flags)
- Produces reviewer_confidence.json with calibration metrics:
  { 'avg_priority', 'std_priority', 'precision_estimate', 'calibrated_confidence' }
"""
import json, math
from pathlib import Path
from statistics import mean, pstdev

HISTORY = Path("review_history.json")
OUT = Path("reviewer_confidence.json")

def load_history():
    if not HISTORY.exists():
        return []
    try:
        return json.loads(HISTORY.read_text())
    except Exception:
        return []

def calibrate(entries):
    scores = [e.get("priority_score", 0) for e in entries if isinstance(e.get("priority_score"), (int,float))]
    if not scores:
        return {"avg_priority": None, "std_priority": None, "calibrated_confidence": 0.5}
    avg = mean(scores)
    std = pstdev(scores) if len(scores)>1 else 0.0
    # heuristic: higher avg priority => confidence to be cautious; lower std => more consistent
    consistency = max(0.0, 1 - std/50)  # roughly 0..1
    calibrated = round(min(1.0, 0.5 + (avg-50)/200 + consistency*0.25), 3)
    return {"avg_priority": round(avg,2), "std_priority": round(std,2), "consistency": round(consistency,3), "calibrated_confidence": calibrated}

def main():
    entries = load_history()
    out = calibrate(entries)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"[INFO] Wrote reviewer_confidence.json: {out}")

if __name__ == "__main__":
    main()
