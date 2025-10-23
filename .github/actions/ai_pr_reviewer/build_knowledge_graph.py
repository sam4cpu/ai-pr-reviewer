import os
import json
import networkx as nx
import matplotlib.pyplot as plt

print("[START] Building Knowledge Graph (Day 17)")

G = nx.Graph()
G.add_node("AI_Reviewer", type="agent")
G.add_node("Predictive_Model", type="module")
G.add_node("Reinforcement_Tuner", type="module")
G.add_node("Knowledge_Graph", type="artifact")
G.add_node("Trend_Analyzer", type="analytics")

edges = [
    ("AI_Reviewer", "Predictive_Model"),
    ("AI_Reviewer", "Reinforcement_Tuner"),
    ("Predictive_Model", "Trend_Analyzer"),
    ("Trend_Analyzer", "Knowledge_Graph"),
    ("Reinforcement_Tuner", "Knowledge_Graph"),
]
G.add_edges_from(edges)

nx.write_gml(G, "knowledge_graph.gml")

summary = f"""
### Knowledge Graph Summary (Day 17)
- **Nodes:** {G.number_of_nodes()}
- **Edges:** {G.number_of_edges()}
- **Core Connections:** AI Reviewer ↔ Predictive Model ↔ Knowledge Graph

> This graph encodes relationships between modules and learning processes for adaptive intelligence transfer.
"""

with open("graph_summary.md", "w") as f:
    f.write(summary.strip())

# Visualization
plt.figure(figsize=(6, 4))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_size=1800, node_color="skyblue", font_size=8)
plt.title("AI Knowledge Graph — Day 17")
plt.tight_layout()
plt.savefig("graph_visualization.png")

# Export embeddings
embeddings = {node: list(map(float, pos[node])) for node in G.nodes}
with open("network_embeddings.json", "w") as f:
    json.dump(embeddings, f, indent=2)

print("[SUCCESS] Knowledge Graph built and saved.")
