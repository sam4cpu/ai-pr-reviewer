"""
Produces final_report.md summarizing the project, key metrics, and "How to run" for recruiters.
Reads: dashboard_summary.json, ai_adaptive_log.json, review_history.json
Writes: final_report.md
"""
import os, json
from datetime import datetime

SUMMARY = "dashboard_summary.json"
ADAPTIVE = "ai_adaptive_log.json"
HISTORY = "review_history.json"
OUT = "final_report.md"

def load(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def short_intro():
    return f"# Final Project Report — AI PR Reviewer (Unified Dashboard v19)\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\nThis repository implements an adaptive, self-evaluating AI PR reviewer with reinforcement tuning, predictive analytics, cross-repo learning, and a generated dashboard for recruiter-facing artifacts.\n\n"

def metrics_section(summary, adaptive):
    lines = []
    lines.append("## Key Metrics (automatically computed)\n")
    if summary:
        lines.append(f"- **Total reviews processed:** {summary.get('total_reviews')}")
        lines.append(f"- **Avg priority score:** {summary.get('avg_priority')}")
        lines.append(f"- **High-risk ratio:** {summary.get('risk_ratio')}%")
        lines.append(f"- **Recent trend:** {summary.get('recent_trend')}\n")
    else:
        lines.append("- No dashboard summary found.\n")
    if adaptive:
        lines.append("### Adaptive snapshot")
        lines.append(f"- avg_recent_priority: {adaptive.get('average_score')}")
        lines.append(f"- adaptive history length: {len(adaptive.get('history',[]))}\n")
    return "\n".join(lines)

def how_to_run():
    return """## How to run locally (for reviewers / engineers)

1. Clone repo
2. Ensure Python 3.10+ and install deps:
