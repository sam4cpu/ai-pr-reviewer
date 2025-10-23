"""
recruiter_report.py — AI PR Reviewer 
Generates a recruiter-facing project summary from recent AI Reviewer outputs.
Highlights intelligence, learning capability, metrics, and professional polish.

Outputs:
  - recruiter_summary.md
  - recruiter_score.json (optional numerical metrics)
"""

from pathlib import Path
import json
from datetime import datetime
from statistics import mean

# Paths to look for
DASHBOARD_SUMMARY = Path("dashboard_summary.json")
WEIGHTS = Path("adaptive_weights.json")
CONFIDENCE = Path("reviewer_confidence.json")
OUTPUT_MD = Path("recruiter_summary.md")
OUTPUT_JSON = Path("recruiter_score.json")

def safe_load_json(path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def compute_project_score(metrics):
    """
    Compute a simple 0–100 score based on:
      - Model adaptability
      - Confidence calibration
      - Predictive insight depth
    """
    adaptability = metrics.get("adaptability", 0)
    confidence = metrics.get("avg_confidence", 0)
    insight = metrics.get("insight_depth", 0)
    # Weighted sum
    return round((0.4 * adaptability + 0.35 * confidence + 0.25 * insight), 2)

def generate_summary():
    dashboard = safe_load_json(DASHBOARD_SUMMARY)
    weights = safe_load_json(WEIGHTS)
    confidence_data = safe_load_json(CONFIDENCE)

    metrics = {
        "total_prs": dashboard.get("total_prs", 0),
        "avg_confidence": dashboard.get("avg_confidence", 75),
        "adaptability": round(weights.get("depth_multiplier", 1.0) * 50, 2),
        "insight_depth": mean([v for v in weights.values() if isinstance(v, (int, float))]) * 10 if weights else 50,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }

    score = compute_project_score(metrics)
    metrics["impact_score"] = score
    OUTPUT_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Markdown summary for recruiters
    md = f"""# AI Reviewer — Recruiter Summary  
*Autonomous Adaptive Code Intelligence System*

**Project Overview**
- Adaptive AI reviewer integrated via GitHub Actions
- Learns from past reviews using self-evaluation & reinforcement tuning
- Predictive and networked intelligence (cross-repo learning)

**Latest Metrics**
| Metric | Value |
|:-------|:------|
| Total PRs Reviewed | {metrics['total_prs']} |
| Avg Confidence | {metrics['avg_confidence']}% |
| Adaptability Index | {metrics['adaptability']} |
| Insight Depth | {metrics['insight_depth']:.2f} |
| Overall Project Impact | **{metrics['impact_score']} / 100** |

**Key Features**
- ⚙️ Multi-phase CI orchestration with self-learning loops  
- 🧠 Predictive & Reinforcement-Learning Components  
- 🌐 Network Fusion: shares intelligence across repositories  
- 📊 Auto-dashboard + recruiter summary generation  

**Verdict**
> *“Demonstrates end-to-end system design, MLOps integration, and adaptive model reasoning.”*

_Last updated: {metrics['timestamp']}_  
"""

    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"[INFO] Recruiter summary generated → {OUTPUT_MD}")
    print(f"[INFO] Impact Score: {score}/100")

if __name__ == "__main__":
    generate_summary()
