import os, json
from datetime import datetime

def load_reviews(base_path="."):
    results = []
    for root, _, files in os.walk(base_path):
        for f in files:
            if f == "review_metadata.json":
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as meta:
                        data = json.load(meta)
                        results.append(data)
                except Exception as e:
                    print(f"[WARN] Failed to read {path}: {e}")
    return results

def summarize(reviews):
    total = len(reviews)
    successes = sum(1 for r in reviews if r.get("success"))
    avg_score = 0
    scores = []
    for r in reviews:
        if "priority_score" in r:
            scores.append(r["priority_score"])
    if scores:
        avg_score = round(sum(scores)/len(scores), 2)

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_reviews": total,
        "successful": successes,
        "average_priority_score": avg_score,
    }

def save_summary(summary):
    with open("review_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("[INFO] Saved review summary to review_summary.json")

    with open("review_summary.md", "w", encoding="utf-8") as f:
        f.write(f"""# 🧠 AI PR Review Summary

**Generated:** {summary['timestamp']}

- Total Reviews: {summary['total_reviews']}
- Successful Runs: {summary['successful']}
- Average Priority Score: {summary['average_priority_score']}

*(Automatically generated analytics report.)*
""")
    print("[INFO] Saved markdown summary report.")

def main():
    reviews = load_reviews(".")
    summary = summarize(reviews)
    save_summary(summary)

if __name__ == "__main__":
    main()
