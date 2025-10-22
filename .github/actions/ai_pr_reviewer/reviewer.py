"""
reviewer.py — Day 17: Reinforcement & Adaptive Tuning Ready

Features:
 - Uses robust_openai with caching + exponential backoff
 - Integrates peer-learning adaptive weights
 - Applies reinforcement tuning to analysis depth & scoring
 - Logs all outputs to artifacts for later self-evaluation
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from robust_openai import request_with_backoff
from peer_learning import load_history, compute_weights

# === Paths ===
REVIEW_OUT = Path("ai_review.md")
SELF_EVAL_OUT = Path("ai_self_eval.json")
METADATA_OUT = Path("review_metadata.json")
HISTORY_OUT = Path("review_history.json")
ADAPTIVE_LOG = Path("ai_adaptive_log.json")

# === Helpers ===
def safe_json_write(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[INFO] Wrote {path.name}")
    except Exception as e:
        print(f"[ERROR] Failed writing {path}: {e}")

def analyze_feedback_priority(feedback_text: str):
    """Tiny heuristic to assign a priority score and categories."""
    text = feedback_text.lower()
    score = 50
    high_risk = False
    category = "general"

    if "security" in text or "vulnerability" in text:
        score += 25
        high_risk = True
        category = "security"
    if "test" in text or "coverage" in text:
        score += 10
        category = "test update"
    if "refactor" in text or "style" in text:
        category = "style"
        score += 5
    if "performance" in text:
        category = "performance"
        score += 8

    score = min(score, 100)
    return {
        "priority_score": score,
        "high_risk": high_risk,
        "category": category
    }

def append_history(entry):
    history = load_history()
    history.append(entry)
    safe_json_write(HISTORY_OUT, history)

# === Main Execution ===
def run_reviewer():
    start_time = time.time()
    print("[START] Day 17 — Reinforcement-Ready AI Reviewer")

    # Load PR diff if available
    diff_path = Path("pr_diff.patch")
    if not diff_path.exists() or diff_path.stat().st_size == 0:
        print("[WARN] No diff file found, skipping analysis.")
        return

    diff_text = diff_path.read_text(encoding="utf-8")

    # Prepare prompt for AI
    prompt = f"""
You are an expert software engineer performing an intelligent PR review.

Analyze the following diff for:
- Code correctness, potential bugs
- Security or performance issues
- Missing tests or documentation
- Suggest concise improvements

Return structured Markdown feedback with sections:
1. Overview
2. Key Findings
3. Recommendations
---
DIFF BELOW:
{diff_text[:8000]}  # truncated if large
"""

    openai_key = os.getenv("OPENAI_API_KEY", "")
    messages = [
        {"role": "system", "content": "You are a senior AI PR reviewer."},
        {"role": "user", "content": prompt.strip()}
    ]

    ai_feedback = request_with_backoff(openai_key, messages, model="gpt-4o-mini")

    if not ai_feedback:
        print("[WARN] No AI feedback available; using fallback text.")
        ai_feedback = "## Mock AI Review\n\nUnable to contact OpenAI API. Generated fallback review."

    REVIEW_OUT.write_text(ai_feedback, encoding="utf-8")
    print("[INFO] Saved AI review to ai_review.md")

    # === Apply adaptive weights ===
    weights = {}
    if Path("adaptive_weights.json").exists():
        try:
            weights = json.loads(Path("adaptive_weights.json").read_text())
            print(f"[INFO] Loaded adaptive weights: {weights}")
        except Exception as e:
            print(f"[WARN] Could not load adaptive weights: {e}")
    else:
        weights = compute_weights(load_history())
        print("[INFO] Using computed baseline adaptive weights.")

    # === Analyze feedback and scale with adaptive tuning ===
    analysis = analyze_feedback_priority(ai_feedback)
    depth_mul = weights.get("depth_multiplier", 1.0)
    analysis["priority_score"] = int(min(100, analysis["priority_score"] * depth_mul))
    analysis["timestamp"] = datetime.utcnow().isoformat()
    analysis["weights_used"] = weights
    analysis["review_length"] = len(ai_feedback)

    append_history(analysis)
    print(f"[INFO] Analysis complete: {analysis}")

    # === Log metadata ===
    metadata = {
        "mode": "reinforcement",
        "openai_key_present": bool(openai_key),
        "adaptive_weights_used": weights,
        "start_time": start_time,
        "end_time": time.time(),
        "duration_sec": round(time.time() - start_time, 2),
    }
    safe_json_write(METADATA_OUT, metadata)

    # === Self-eval stub (for next step in workflow) ===
    self_eval = {
        "ai_self_score": analysis["priority_score"] / 1.2,
        "confidence": weights.get("depth_multiplier", 1.0),
        "timestamp": datetime.utcnow().isoformat()
    }
    safe_json_write(SELF_EVAL_OUT, self_eval)

    # === Adaptive log ===
    adaptive_log = {
        "weights": weights,
        "final_priority_score": analysis["priority_score"],
        "review_len": analysis["review_length"]
    }
    safe_json_write(ADAPTIVE_LOG, adaptive_log)

    print("[SUCCESS] Day 17 Reinforcement-Ready Review completed.")
    return 0


if __name__ == "__main__":
    try:
        run_reviewer()
    except Exception as e:
        print(f"[FATAL] Reviewer crashed: {e}")
        raise

















