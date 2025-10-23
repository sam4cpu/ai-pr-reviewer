"""
generate_dashboard_v19.py
Reads: review_history.json, ai_adaptive_log.json, ai_review.md, optional predictive outputs
Writes: dashboard_v19.html, dashboard_summary.json, charts (png)
"""
import os
import json
from datetime import datetime
from statistics import mean
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "."
HISTORY = os.path.join(ROOT, "review_history.json")
ADAPTIVE = os.path.join(ROOT, "ai_adaptive_log.json")
REVIEW_MD = os.path.join(ROOT, "ai_review.md")
OUT_HTML = os.path.join(ROOT, "dashboard_v19.html")
SUMMARY_JSON = os.path.join(ROOT, "dashboard_summary.json")

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def make_plots(history):
    # history: list of entries with timestamp, priority_score, category, high_risk
    timestamps = [h.get("timestamp") for h in history if h.get("timestamp")]
    scores = [h.get("priority_score", 0) for h in history]
    cats = {}
    high_risk_counts = [1 if h.get("high_risk") else 0 for h in history]

    for h in history:
        cat = h.get("category", "uncategorized")
        cats[cat] = cats.get(cat, 0) + 1

    # Priority over time
    if scores:
        plt.figure(figsize=(8,3))
        plt.plot(range(len(scores)), scores, marker='o', linewidth=1)
        plt.title("Priority Score over Reviews")
        plt.ylabel("Priority score")
        plt.xlabel("Recent reviews (time order)")
        plt.tight_layout()
        p1 = "chart_priority_time.png"
        plt.savefig(p1)
        plt.close()
    else:
        p1 = None

    # Category distribution
    if cats:
        plt.figure(figsize=(6,3))
        labels = list(cats.keys())
        vals = [cats[k] for k in labels]
        plt.bar(range(len(vals)), vals)
        plt.xticks(range(len(vals)), labels, rotation=45, ha='right')
        plt.title("Category distribution")
        plt.tight_layout()
        p2 = "chart_category_dist.png"
        plt.savefig(p2)
        plt.close()
    else:
        p2 = None

    # High risk count over time (rolling sum)
    if high_risk_counts:
        import numpy as _np
        roll = []
        window = max(1, min(8, len(high_risk_counts)))
        arr = _np.array(high_risk_counts)
        for i in range(len(arr)):
            roll.append(float(arr[max(0, i-window+1):i+1].sum()))
        plt.figure(figsize=(8,3))
        plt.plot(range(len(roll)), roll, marker='o')
        plt.title(f"High-risk upstream count (rolling {window})")
        plt.ylabel("high-risk count")
        plt.xlabel("Recent reviews")
        plt.tight_layout()
        p3 = "chart_highrisk.png"
        plt.savefig(p3)
        plt.close()
    else:
        p3 = None

    return p1, p2, p3

def build_html(summary, charts, review_snippet):
    # minimal, self-contained HTML
    now = datetime.utcnow().isoformat() + "Z"
    p1, p2, p3 = charts
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"><title>AI Reviewer Dashboard v19</title>
  <style>
    body{{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial; margin:24px}}
    header{{margin-bottom:20px}}
    .metrics{{display:flex;gap:20px;flex-wrap:wrap}}
    .card{{padding:12px;border-radius:8px;background:#f6f8fa;min-width:180px}}
    img{{max-width:100%;border:1px solid #ddd;padding:6px;background:white}}
    pre{{background:#111;color:#dcdcdc;padding:12px;border-radius:6px;overflow:auto}}
  </style>
</head>
<body>
  <header>
    <h1>AI PR Reviewer — Unified Dashboard (v19)</h1>
    <p>Generated: {now}</p>
  </header>

  <section class="metrics">
    <div class="card"><strong>Total reviews</strong><div>{summary.get("total_reviews")}</div></div>
    <div class="card"><strong>Avg priority</strong><div>{summary.get("avg_priority")}</div></div>
    <div class="card"><strong>High risk %</strong><div>{summary.get("risk_ratio")}%</div></div>
    <div class="card"><strong>Recent trend</strong><div>{summary.get("recent_trend")}</div></div>
  </section>

  <h2>Charts</h2>
  <div>
    {"<img src='" + p1 + "' alt='priority time'/>" if p1 else ""}
    {"<img src='" + p2 + "' alt='category dist'/>" if p2 else ""}
    {"<img src='" + p3 + "' alt='high risk'/>" if p3 else ""}
  </div>

  <h2>Latest AI Review (snippet)</h2>
  <pre>{(review_snippet or "")[:1200]}</pre>

  <h2>Summary JSON</h2>
  <pre>{json.dumps(summary, indent=2)}</pre>

  <footer style="margin-top:24px;color:#666">AI PR Reviewer — Dashboard v19</footer>
</body>
</html>"""
    return html

def summarize_history(history):
    metrics = {}
    if not history:
        metrics = {"total_reviews":0,"avg_priority":None,"risk_ratio":0.0,"recent_trend":None}
        return metrics
    scores = [h.get("priority_score",0) for h in history if isinstance(h.get("priority_score"), (int,float))]
    avg_score = round(mean(scores),2) if scores else None
    total = len(history)
    high = sum(1 for h in history if h.get("high_risk"))
    risk_ratio = round( (high/total) * 100, 2) if total else 0.0
    # simple recent trend: compare last 5 vs previous 5
    last = scores[-5:] if len(scores)>=1 else []
    prev = scores[-10:-5] if len(scores)>=6 else []
    trend = None
    try:
        if last and prev:
            trend = "improving" if mean(last) > mean(prev)+2 else ("declining" if mean(last) < mean(prev)-2 else "stable")
    except Exception:
        trend = None
    return {"total_reviews": total, "avg_priority": avg_score, "risk_ratio": risk_ratio, "recent_trend": trend}

def main():
    history = load_json(HISTORY) or []
    adaptive = load_json(ADAPTIVE) or {}
    review_md = safe_read(REVIEW_MD) or ""
    # compute summary
    summary = summarize_history(history)
    # create charts
    p1,p2,p3 = make_plots(history)
    # write summary json
    summary["adaptive_snapshot"] = {
        "avg_recent_priority": adaptive.get("average_score"),
        "log_len": len(adaptive.get("history", []))
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    # build html
    html = build_html(summary, (p1,p2,p3), review_md)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Dashboard written to {OUT_HTML}")
    print(f"[INFO] Summary written to {SUMMARY_JSON}")
    # print artifact list
    print("[DONE] Charts:", p1, p2, p3)

if __name__ == "__main__":
    main()
