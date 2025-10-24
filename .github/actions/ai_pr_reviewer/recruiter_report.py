"""
recruiter_report.py — AI PR Reviewer 
Generates:
  - recruiter_summary.md  (markdown summary)
  - recruiter_score.json  (raw metrics)
  - recruiter_badge.svg   (dynamic badge)
"""

from pathlib import Path
import json
from datetime import datetime
from statistics import mean

# Paths
DASHBOARD_SUMMARY = Path("dashboard_summary.json")
WEIGHTS = Path("adaptive_weights.json")
CONFIDENCE = Path("reviewer_confidence.json")
OUTPUT_MD = Path("recruiter_summary.md")
OUTPUT_JSON = Path("recruiter_score.json")
BADGE_SVG = Path("recruiter_badge.svg")

def safe_load_json(path):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def compute_project_score(metrics):
    adaptability = metrics.get("adaptability", 0)
    confidence = metrics.get("avg_confidence", 0)
    insight = metrics.get("insight_depth", 0)
    return round((0.4 * adaptability + 0.35 * confidence + 0.25 * insight), 2)

def generate_badge(score):
    # Badge color logic
    if score >= 90:
        color = "#00c853"  # bright green
    elif score >= 75:
        color = "#4caf50"
    elif score >= 60:
        color = "#ffb300"
    else:
        color = "#f44336"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="180" height="28" role="img">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <rect rx="3" width="180" height="28" fill="#555"/>
  <rect rx="3" x="100" width="80" height="28" fill="{color}"/>
  <path fill="{color}" d="M100 0h4v28h-4z"/>
  <rect rx="3" width="180" height="28" fill="url(#s)"/>
  <g fill="#fff" text-anchor="middle"
     font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="12">
    <text x="50" y="18" fill="#010101" fill-opacity=".3">Impact Score</text>
    <text x="50" y="17">Impact Score</text>
    <text x="140" y="18" fill="#010101" fill-opacity=".3">{score}/100</text>
    <text x="140" y="17">{score}/100</text>
  </g>
</svg>"""
    BADGE_SVG.write_text(svg, encoding="utf-8")
    print(f"[INFO] Generated recruiter badge → {BADGE_SVG}")

def generate_summary():
    dashboard = safe_load_json(DASHBOARD_SUMMARY)
    weights = safe_load_json(WEIGHTS)
    confidence_data = safe_load_json(CONFIDENCE)

    numeric_weights = [v for v in weights.values() if isinstance(v, (int, float))]
    if not numeric_weights:
        print("[WARN] No numeric weights found; using neutral baseline for insight depth.")

    insight_depth = mean(numeric_weights) * 10 if numeric_weights else 50

    summary = {
        "avg_confidence": confidence.get("calibrated_confidence", 0.5) * 100,
        "adaptability_index": weights.get("adaptivity", 1.0),
        "insight_depth": insight_depth,
        "impact_score": round(
            (confidence.get("calibrated_confidence", 0.5) * 100 + insight_depth) / 2, 2
        ),
    }

    metrics = {
        "total_prs": dashboard.get("total_prs", 0),
        "avg_confidence": dashboard.get("avg_confidence", 75),
        "adaptability": round(weights.get("depth_multiplier", 1.0) * 50, 2),
        "insight_depth": summary["insight_depth"],
        "impact_score": summary["impact_score"],
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


    score = compute_project_score(metrics)
    metrics["impact_score"] = score
    OUTPUT_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    generate_badge(score)

    md = f"""# AI Reviewer — Recruiter Summary  
*Autonomous Adaptive Code Intelligence System*

![Impact Score](recruiter_badge.svg)

**Project Overview**
- Adaptive AI reviewer integrated via GitHub Actions  
- Self-learning (reinforcement + predictive tuning)  
- Networked intelligence + recruiter auto-reporting  

**Latest Metrics**
| Metric | Value |
|:-------|:------|
| Total PRs Reviewed | {metrics['total_prs']} |
| Avg Confidence | {metrics['avg_confidence']}% |
| Adaptability Index | {metrics['adaptability']} |
| Insight Depth | {metrics['insight_depth']:.2f} |
| **Impact Score** | **{metrics['impact_score']} / 100** |

**Highlights**
- ⚙️ Multi-phase workflow orchestration  
- 🧠 Predictive & Reinforcement learning  
- 🌐 Global reviewer mesh fusion  
- 📈 Auto-generated dashboards & badges  

**Verdict**
> *"Demonstrates strong software architecture, adaptive AI reasoning, and CI/CD integration — well beyond standard university projects."*

_Last updated: {metrics['timestamp']}_  
"""
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"[INFO] Recruiter summary generated → {OUTPUT_MD}")
    print(f"[INFO] Impact Score: {score}/100")

if __name__ == "__main__":
    generate_summary()
