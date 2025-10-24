# AI PR Reviewer — Autonomous Adaptive Code Intelligence

![Impact Score](https://github.com/sam4cpu/ai-pr-reviewer/blob/main/recruiter_badge.svg)

> **Autonomous AI system** for pull-request review, continuous self-learning, and cross-repository intelligence — built using multi-phase GitHub Actions workflows, reinforcement tuning, and predictive analysis.

---

## Overview

AI PR Reviewer is an **AI-driven code review assistant** that continuously improves its reasoning quality through:
- **Adaptive Reinforcement Learning** — adjusts review weights based on past accuracy and self-evaluations.  
- **Predictive Insight Models** — anticipates likely review patterns and defects.   
- **Networked Reviewer Mesh** — shares learning data across repositories to build a global code-intelligence layer.  
- **Recruiter Analytics Mode ** — auto-generates visual badges and recruiter summaries after each run.

---

## Architecture

| Layer | Description |
|:------|:-------------|
| **Workflow Orchestration** | Multi-phase GitHub Actions (`ai_pr_reviewer.yml`) coordinating review, analysis, tuning, and dashboard generation. |
| **Reviewer Engine** | Python modules (`reviewer.py`, `reinforcement_tuner.py`, `reviewer_predictive.py`) executing structured PR analysis and self-evaluation. |
| **Adaptive Weights** | Stored in `adaptive_weights.json` — dynamically tuned each CI run. |
| **Visualization** | `dashboard_v18.html` and `recruiter_badge.svg` summarize performance. |

---

## 📈 Example Output

### Recruiter Badge  
![Impact Score](recruiter_badge.svg)

### Dashboard Preview  
*(generated automatically via `generate_dashboard_v18.py`)*  

![Dashboard Screenshot](.github/assets/dashboard_preview.png)

## Key Metrics

| Metric | Example Value |
|:--------|:---------------|
| Avg Confidence | 87 % |
| Adaptability Index | 1.42× |
| Insight Depth | 92/100 |
| Impact Score | **94 / 100** |

---

Technical Highlights
- **Multi-phase CI/CD architecture** using modular GitHub Actions jobs.  
- **Reinforcement heuristics** (reward matrix + adaptive weight fusion).  
- **Predictive trend modeling** with lightweight local training (`train_predictive_model.py`).  
- **Global Hub Sync** — allows cross-repo knowledge aggregation via secure PAT.  
- **Self-evaluation loop** producing metrics and visual dashboards automatically.

---

## Stack

- Python 3.10 + NumPy / Pandas / Matplotlib / scikit-learn  
- GitHub Actions (multi-job, artifact-driven workflows)  
- OpenAI API (for natural-language review generation)  
- JSON-based adaptive model persistence  

---

## Recruiter Summary

The project automatically generates:

- `recruiter_summary.md` — concise performance overview  
- `recruiter_score.json` — raw metric data  
- `recruiter_badge.svg` — auto-updating visual badge  

> “Demonstrates strong system design, applied AI reasoning, and CI/CD automation — exceeding expectations for early-career SWE level.”

---

## Setup & Run

1. **Clone the repo**  
   ```bash
   git clone https://github.com/sam4cpu/ai-pr-reviewer.git
   cd ai-pr-reviewer

