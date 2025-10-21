import json
import os
from datetime import datetime
import statistics
from openai import OpenAI

def load_json(path, default=None):
    """Utility to load JSON safely."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def compute_learning_metrics(history, self_eval):
    """Derive learning signals from AI review performance."""
    scores = [item.get("priority_score", 0) for item in history if "priority_score" in item]
    high_risk = sum(1 for i in history if i.get("high_risk"))
    total_reviews = len(history)
    
    avg_score = statistics.mean(scores) if scores else 0
    clarity = self_eval.get("clarity", 0)
    actionability = self_eval.get("actionability", 0)
    cqi = self_eval.get("cqi", 0)

    learning_index = (avg_score * 0.4) + (clarity * 0.2) + (actionability * 0.2) + (cqi * 0.2)
    stability = 100 - (high_risk / total_reviews * 100 if total_reviews > 0 else 0)

    return {
        "avg_priority_score": round(avg_score, 2),
        "high_risk_count": high_risk,
        "total_reviews": total_reviews,
        "clarity": clarity,
        "actionability": actionability,
        "cqi": cqi,
        "learning_index": round(learning_index, 2),
        "stability": round(stability, 2)
    }

def generate_improvement_plan(metrics):
    """Formulate an actionable improvement plan for next reviews."""
    plan = []

    if metrics["clarity"] < 80:
        plan.append("Increase feedback clarity with concise phrasing and bullet points.")
    if metrics["actionability"] < 80:
        plan.append("Provide more specific, code-oriented suggestions with rationale.")
    if metrics["avg_priority_score"] < 70:
        plan.append("Enhance issue detection accuracy and severity classification.")
    if metrics["stability"] < 85:
        plan.append("Reduce high-risk flags by strengthening validation checks.")
    if metrics["learning_index"] > 85:
        plan.append("Maintain current learning parameters and consistency.")

    plan.append("Re-evaluate recent PRs to verify feedback accuracy trend.")
    plan.append("Fine-tune tone balance (constructive vs. critical) adaptively.")

    return plan

def generate_quality_report(metrics, plan):
    """Generate a human-readable Markdown summary."""
    report = f"""
# 🤖 AI Continuous Learning Report — Day 14

**Generated:** {datetime.utcnow().isoformat()}Z

### 📊 Learning Metrics
- Average Priority Score: **{metrics['avg_priority_score']}**
- Clarity: **{metrics['clarity']}**
- Actionability: **{metrics['actionability']}**
- CQI (Consistency Quality Index): **{metrics['cqi']}**
- Learning Index: **{metrics['learning_index']}**
- Stability: **{metrics['stability']}%**
- High-Risk Flags: **{metrics['high_risk_count']}**
- Total Reviews Processed: **{metrics['total_reviews']}**

### 🧠 Improvement Plan
{chr(10).join(f"- {p}" for p in plan)}

### 🔁 Next Steps
1. Apply improvement plan feedback in adaptive context generation.
2. Compare new review cycles with this baseline.
3. Save model deltas for Day 15 (Reinforcement Learning Feedback).
"""
    return report

def run_continuous_learning():
    """Main Day 14 logic."""
    print("[START] Running Continuous Learning Core ")

    history = load_json("review_history.json", [])
    self_eval = load_json("ai_self_eval.json", {})

    if not history:
        print("[WARN] No review history found. Skipping learning cycle.")
        return

    metrics = compute_learning_metrics(history, self_eval)
    plan = generate_improvement_plan(metrics)
    report = generate_quality_report(metrics, plan)

    os.makedirs("learning_outputs", exist_ok=True)

    with open("learning_outputs/improvement_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    with open("learning_outputs/self_eval_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open("learning_outputs/quality_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("[SUCCESS] Continuous Learning Artifacts Generated:")
    print(" - improvement_plan.json")
    print(" - self_eval_metrics.json")
    print(" - quality_report.md")

if __name__ == "__main__":
    run_continuous_learning()

