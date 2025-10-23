"""
generate_dashboard_v18.py
- Loads: ai_predictive_insights.json, reward_matrix.json, adaptive_network_weights.json, reviewer_confidence.json
- Produces: dashboard_v18.html and dashboard_summary.json
Uses plotly offline to generate an interactive HTML file suitable for artifacts.
"""
import json
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def safe_load(path):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

predictive = safe_load("ai_predictive_insights.json")
reward = safe_load("reward_matrix.json")
network = safe_load("adaptive_network_weights.json")
confidence = safe_load("reviewer_confidence.json")

fig = make_subplots(rows=2, cols=2, subplot_titles=("Predictive Insights","Reward Matrix","Network Weights","Reviewer Confidence"))

# Predictive panel
if predictive:
    keys = list(predictive.keys())
    vals = [predictive[k] if isinstance(predictive[k], (int,float)) else len(str(predictive[k])) for k in keys]
    fig.add_trace(go.Bar(x=keys, y=vals, name="Predictive"), row=1, col=1)

# Reward
if reward:
    base = reward.get("base_reward", 0)
    fig.add_trace(go.Indicator(mode="gauge+number", value=base, title={"text":"Base Reward"}, gauge={"axis":{"range":[0,100]}}), row=1, col=2)

# Weights
if network:
    if isinstance(network, dict) and "weights" in network:
        w = network["weights"]
    else:
        w = network
    fig.add_trace(go.Bar(x=list(w.keys()), y=[float(w[k]) if isinstance(w[k],(int,float)) else 0 for k in w.keys()], name="Network Weights"), row=2, col=1)

# Confidence
if confidence:
    val = confidence.get("calibrated_confidence", 0)
    fig.add_trace(go.Indicator(mode="number+gauge", value=val, title={"text":"Calibrated Confidence"}, gauge={"axis":{"range":[0,1]}}), row=2, col=2)

fig.update_layout(height=800, title_text="AI Reviewer Mesh — Day 18 Dashboard")
OUT_HTML = "dashboard_v18.html"
fig.write_html(OUT_HTML, include_plotlyjs='cdn')

summary = {
    "predictive_keys": list(predictive.keys())[:6],
    "base_reward": reward.get("base_reward") if reward else None,
    "network_weight_keys": list(w.keys())[:6] if 'w' in locals() else [],
    "calibrated_confidence": confidence.get("calibrated_confidence") if confidence else None
}
Path("dashboard_summary.json").write_text(json.dumps(summary, indent=2))
print("[INFO] dashboard_v18.html and dashboard_summary.json written.")

