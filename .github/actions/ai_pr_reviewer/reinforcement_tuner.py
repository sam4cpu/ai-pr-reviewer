import json
import os
from datetime import datetime
import numpy as np

def calculate_reward(entry):
    """Compute a reward score based on review performance proxies."""
    base = entry.get("priority_score", 0) / 100
    clarity = min(1.0, entry.get("clarity_score", 0.0))
    actionability = min(1.0, entry.get("actionability", 0.0))
    penalty = 0.2 if entry.get("high_risk") else 0.0

    return max(0.0, base * 0.6 + clarity * 0.25 + actionability * 0.25 - penalty)


def update_adaptive_weights(log_file="reward_log.json", output_file="adaptive_weights.json"):
    """Use recent performance logs to update model tuning weights."""
    if not os.path.exists(log_file):
        print("[WARN] No reinforcement logs found.")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        logs = json.load(f)

    if not logs:
        print("[WARN] Empty reinforcement log file.")
        return

    rewards = [calculate_reward(entry) for entry in logs[-30:]]
    avg_reward = np.mean(rewards)
    std_reward = np.std(rewards)

    weights = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "avg_reward": float(avg_reward),
        "stability": float(max(0.0, 1 - std_reward)),
        "clarity_weight": float(np.clip(avg_reward + 0.05, 0, 1)),
        "actionability_weight": float(np.clip(avg_reward, 0, 1)),
        "risk_penalty": float(np.clip(1 - avg_reward, 0.2, 1.0)),
    }

    # Save new adaptive weights
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2)

    print(f"[INFO] Adaptive weights updated — avg_reward={avg_reward:.3f}, stability={weights['stability']:.3f}")
    return weights


def main():
    print("[START] Running reinforcement tuner...")
    weights = update_adaptive_weights()
    if weights:
        report = f"""### Reinforcement Summary (Day 15)
- Avg Reward: {weights['avg_reward']:.3f}
- Stability: {weights['stability']:.3f}
- Clarity Weight: {weights['clarity_weight']:.2f}
- Actionability Weight: {weights['actionability_weight']:.2f}
- Risk Penalty: {weights['risk_penalty']:.2f}
"""
        with open("reinforcement_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        print("[SUCCESS] Reinforcement report generated.")


if __name__ == "__main__":
    main()
