import json
from pathlib import Path
import matplotlib.pyplot as plt
from statistics import mean

from robust_openai import analyze_diff, safe_openai_call
from peer_learning import load_history, compute_weights, write_weights

HISTORY = Path("review_history.json")
SELF_EVAL = Path("ai_self_eval.json")
ADAPTIVE_WEIGHTS = Path("adaptive_weights.json")
METRICS_IMG = Path("ai_review_metrics.png")

def visualize_metrics(reward_matrix, weights):
    """
    Generates an introspection plot showing reviewer intelligence metrics.
    """
    try:
        plt.figure(figsize=(8, 4))
        bars = {
            "Base Reward": reward_matrix.get("base_reward", 0),
            "Avg Priority": reward_matrix.get("avg_priority", 0),
            "Depth Mult.": weights.get("depth_multiplier", 1.0) * 100,
            "Security Bias": weights.get("security_bias", 1.0) * 100,
        }
        plt.bar(bars.keys(), bars.values())
        plt.title("AI Reviewer Intelligence Metrics")
        plt.ylabel("Scaled Score")
        plt.grid(alpha=0.3, linestyle="--")
        for i, (label, val) in enumerate(bars.items()):
            plt.text(i, val + 1, f"{val:.1f}", ha="center", fontsize=9)
        plt.tight_layout()
        plt.savefig(METRICS_IMG)
        plt.close()
        print(f"[INFO] Saved visualization to {METRICS_IMG}")
        return True
    except Exception as e:
        print(f"[WARN] Failed to generate visualization: {e}")
        return False

def embed_visual_in_report(report_path="ai_review.md"):
    """
    Inserts markdown image link at top of the main review report.
    """
    try:
        p = Path(report_path)
        if not p.exists() or not METRICS_IMG.exists():
            return
        content = p.read_text(encoding="utf-8")
        header = "### AI Reviewer Intelligence Overview\n\n"
        img_md = f"![AI Reviewer Metrics]({METRICS_IMG.name})\n\n"
        if img_md not in content:
            new_content = header + img_md + content
            p.write_text(new_content, encoding="utf-8")
            print("[INFO] Embedded metrics visualization in report.")
    except Exception as e:
        print(f"[WARN] Failed to embed visualization: {e}")

def main():
    print("[START] Running AI Reviewer — Day 18 (Visualization Upgrade)")
    history = load_history()

    # Analyze diff (as before)
    review_data = analyze_diff()
    Path("ai_review.md").write_text(review_data["review_text"], encoding="utf-8")
    print("[INFO] Saved main review report.")

    # Load weights and compute reward matrix (using your reinforcement_tuner logic)
    from reinforcement_tuner import compute_rewards, adjust_weights_with_rewards
    self_eval = json.loads(SELF_EVAL.read_text(encoding="utf-8")) if SELF_EVAL.exists() else {}
    reward_matrix = compute_rewards(history, self_eval)

    weights = compute_weights(history)
    weights = adjust_weights_with_rewards(weights, reward_matrix)
    write_weights(weights)

    # Visualize and embed
    visualize_metrics(reward_matrix, weights)
    embed_visual_in_report()

    print("[SUCCESS] AI Reviewer Day 18 complete — report and visualization generated.")

if __name__ == "__main__":
    main()

















