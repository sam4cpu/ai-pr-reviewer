import json
from pathlib import Path
from statistics import mean
from peer_learning import load_history, compute_weights, write_weights

HISTORY = Path("review_history.json")
SELF_EVAL = Path("ai_self_eval.json")
REWARD_OUT = Path("reward_matrix.json")

def load_self_eval():
    if not SELF_EVAL.exists():
        return []
    try:
        return json.loads(SELF_EVAL.read_text(encoding="utf-8"))
    except Exception:
        return []

def compute_rewards(history, self_eval):
    """
    Very small reward heuristic:
      - baseline reward = 50
      - + (self_eval.ai_self_score * 0.3) if present
      - + (avg_priority_score * 0.2)
      - reward per-category computed as normalized counts
    """
    rewards = {}
    avg_priority = mean([h.get("priority_score",0) for h in history]) if history else 0
    self_score = self_eval.get("ai_self_score") if (isinstance(self_eval, dict) and "ai_self_score" in self_eval) else None

    base = 50 + (avg_priority * 0.2)
    if self_score:
        base += self_score * 0.3

    # per-category reward (counts)
    counts = {}
    for e in history:
        cat = e.get("category","general")
        counts[cat] = counts.get(cat, 0) + 1
    total = sum(counts.values()) or 1
    per_cat = {k: round((v/total)*100,2) for k,v in counts.items()}

    reward_matrix = {
        "base_reward": round(base,2),
        "per_category": per_cat,
        "history_len": len(history),
        "avg_priority": round(avg_priority,2),
        "self_eval_score": self_score
    }
    return reward_matrix

def adjust_weights_with_rewards(weights, reward_matrix):
    # small heuristic: if avg_priority high -> increase depth multiplier; else dampen
    if reward_matrix["avg_priority"] > 60:
        weights["depth_multiplier"] = round(weights.get("depth_multiplier",1.0) * 1.05,3)
    else:
        weights["depth_multiplier"] = round(weights.get("depth_multiplier",1.0) * 0.98,3)
    # if base_reward high increase security bias
    if reward_matrix["base_reward"] > 60:
        weights["security_bias"] = round(weights.get("security_bias",1.0) * 1.03,3)
    return weights

def run():
    history = load_history()
    self_eval = {}
    if SELF_EVAL.exists():
        try:
            self_eval = json.loads(SELF_EVAL.read_text(encoding="utf-8"))
        except:
            self_eval = {}
    reward = compute_rewards(history, self_eval)
    REWARD_OUT.write_text(json.dumps(reward, indent=2), encoding="utf-8")
    print(f"[INFO] Wrote reward matrix to {REWARD_OUT}")

    # compute base weights then adjust
    weights = compute_weights(history)
    weights = adjust_weights_with_rewards(weights, reward)
    write_weights(weights)
    return reward, weights

if __name__ == "__main__":
    run()

