"""
Simple static dashboard generator.
Aggregates review + learning artifacts into a visual HTML summary.
"""

import json, os, datetime, pathlib

ARTIFACTS = [
    "review_summary.json",
    "review_history.json",
    "ai_self_eval.json",
    "adaptive_weights.json",
    "reward_matrix.json",
]

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def html_card(title, body):
    return f"""
    <div style='padding:1em;border-radius:10px;background:#f5f5f5;margin:1em 0'>
      <h3>{title}</h3>
      <pre style='white-space:pre-wrap'>{body}</pre>
    </div>
    """

def main():
    parts = []
    for path in ARTIFACTS:
        data = load_json(path)
        if data:
            pretty = json.dumps(data, indent=2)[:4000]  # truncate long
            parts.append(html_card(path, pretty))
        else:
            parts.append(html_card(path, "(missing)"))
    timestamp = datetime.datetime.utcnow().isoformat()
    html = f"""
    <html>
    <head><title>AI PR Reviewer Dashboard</title></head>
    <body style='font-family:monospace;background:#fafafa;padding:2em'>
      <h1>AI PR Reviewer — Continuous Learning Dashboard</h1>
      <p>Generated: {timestamp} UTC</p>
      {''.join(parts)}
    </body></html>
    """
    os.makedirs("dashboard", exist_ok=True)
    out = pathlib.Path("dashboard/index.html")
    out.write_text(html)
    print(f"[DASHBOARD] Wrote {out}")

if __name__ == "__main__":
    main()
