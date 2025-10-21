import json
import os
from datetime import datetime

def analyze_review_history(history_path="review_history.json"):
    """
    Analyze recent PR reviews to determine AI tone and depth.
    Returns a context dict: tone, depth, caution_level, trend_summary
    """
    if not os.path.exists(history_path):
        print("[INFO] No review history found. Using default adaptive settings.")
        return {
            "tone": "neutral",
            "depth": "standard",
            "caution_level": "normal",
            "trend_summary": "No historical data available."
        }

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except json.JSONDecodeError:
        print("[WARN] Corrupted history file. Resetting adaptation context.")
        return {
            "tone": "neutral",
            "depth": "standard",
            "caution_level": "normal",
            "trend_summary": "History file invalid or empty."
        }

    if not history:
        return {
            "tone": "neutral",
            "depth": "standard",
            "caution_level": "normal",
            "trend_summary": "History empty."
        }
      
    recent = history[-10:]  # use last 10 PRs
    avg_priority = sum(item.get("priority_score", 0) for item in recent) / len(recent)
    high_risk_count = sum(1 for item in recent if item.get("high_risk", False))

    # Define logic
    if avg_priority < 30 and high_risk_count == 0:
        tone = "concise"
        depth = "light"
        caution = "low"
        summary = "PRs have been low-risk and consistent."
    elif avg_priority < 70:
        tone = "balanced"
        depth = "standard"
        caution = "normal"
        summary = "PRs show moderate risk; maintaining balanced analysis."
    else:
        tone = "cautious"
        depth = "deep"
        caution = "high"
        summary = "Recent PRs indicate high-risk patterns; increasing scrutiny."

    print(f"[ADAPTIVE] Avg priority: {avg_priority:.1f}, High risk PRs: {high_risk_count}")
    print(f"[ADAPTIVE] Adjusted tone: {tone}, depth: {depth}, caution: {caution}")

    return {
        "tone": tone,
        "depth": depth,
        "caution_level": caution,
        "trend_summary": summary
    }


def log_adaptation(decision, output_path="ai_adaptive_log.json"):
    """Save adaptive decisions with timestamp for transparency."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision": decision
    }

    existing = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            pass

    existing.append(entry)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    print("[INFO] Adaptive behavior logged to ai_adaptive_log.json")
