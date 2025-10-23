import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def safe_load(path):
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

# Load data
predictive = safe_load("ai_predictive_insights.json")
reward = safe_load("reward_matrix.json")
graph = safe_load("knowledge_graph.json")

# Construct figures
fig = make_subplots(rows=1, cols=3, subplot_titles=("Predictive Trends", "Reward Stability", "Knowledge Graph Nodes"))

#  Predictive Trends
if predictive:
    fig.add_trace(
        go.Bar(x=list(predictive.keys()), y=list(predictive.values()), name="Predictive Scores"),
        row=1, col=1
    )

# Reward Stability
if reward:
    base = reward.get("base_reward", 0)
    fig.add_trace(
        go.Indicator(mode="gauge+number", value=base, title={"text": "Reward Stability"}, gauge={"axis": {"range": [0, 100]}}),
        row=1, col=2
    )

# Knowledge Graph Overview
if graph:
    nodes = len(graph.get("nodes", []))
    edges = len(graph.get("edges", []))
    fig.add_trace(
        go.Indicator(mode="number", value=nodes, title={"text": f"Graph Nodes ({edges} edges)"}),
        row=1, col=3
    )

fig.update_layout(title_text=" AI PR Reviewer — Unified Intelligence Dashboard", height=600)
fig.write_html("dashboard_v17.html")

summary = {
    "predictive_factors": list(predictive.keys())[:5],
    "reward_base": reward.get("base_reward"),
    "graph_nodes": len(graph.get("nodes", []))
}
Path("dashboard_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("[INFO] Dashboard generated successfully — saved as dashboard.html")
