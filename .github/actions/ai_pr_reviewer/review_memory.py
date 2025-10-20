"""
Full-featured review memory system for AI PR Reviewer (Day 11).

Responsibilities:
- Persist review entries to review_history.json
- Avoid duplicates (by pr_number or content_hash)
- Keep history bounded (max_entries)
- Compute metrics for adaptive behaviour:
  - avg_priority_score
  - per-category counts
  - high-risk frequency
  - simple trend (improving/declining) based on recent scores
- Provide a simple update_entry(...) API for integration with reviewer.py
"""

import os
import json
import hashlib
from datetime import datetime
from statistics import mean

HISTORY_PATH = "review_history.json"
MAX_ENTRIES = 200  


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def _compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_history(path: str = HISTORY_PATH) -> list:
    """Load history from disk; return empty list if missing or invalid."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            # If someone stored an object, try to recover list under 'entries'
            if isinstance(data, dict) and "entries" in data:
                return data["entries"]
    except Exception as e:
        print(f"[WARN] Could not load history ({path}): {e}")
    return []


def save_history(entries: list, path: str = HISTORY_PATH):
    """Save history to disk (atomic-ish): write to temp then rename."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        print(f"[INFO] Saved {len(entries)} history entries to {path}")
    except Exception as e:
        print(f"[ERROR] Failed to save history: {e}")


def trim_history(entries: list, max_entries: int = MAX_ENTRIES) -> list:
    """Trim to most recent max_entries (history is ordered oldest->newest)."""
    if len(entries) <= max_entries:
        return entries
    return entries[-max_entries:]


def find_duplicate(entries: list, pr_number: str = None, content_hash: str = None):
    """Return index of duplicate entry if found, else None."""
    for i, e in enumerate(entries):
        if pr_number and e.get("pr_number") == pr_number:
            return i
        if content_hash and e.get("content_hash") == content_hash:
            return i
    return None


def compute_metrics(entries: list) -> dict:
    """Compute aggregate metrics from the history entries."""
    if not entries:
        return {
            "total_reviews": 0,
            "avg_priority_score": None,
            "per_category": {},
            "high_risk_count": 0,
            "risk_ratio": 0.0,
            "recent_trend": None,
        }

    scores = [e.get("priority_score") for e in entries if isinstance(e.get("priority_score"), (int, float))]
    avg_score = round(mean(scores), 2) if scores else None

    per_cat = {}
    for e in entries:
        cat = e.get("category", "uncategorized")
        per_cat[cat] = per_cat.get(cat, 0) + 1

    high_risk_count = sum(1 for e in entries if e.get("high_risk"))
    risk_ratio = round(high_risk_count / len(entries) * 100, 2)

    # compare average of last N to previous N
    window = 10
    recent = [e.get("priority_score") for e in entries[-window:] if isinstance(e.get("priority_score"), (int, float))]
    previous = [e.get("priority_score") for e in entries[-2*window:-window] if isinstance(e.get("priority_score"), (int, float))]
    recent_mean = mean(recent) if recent else None
    prev_mean = mean(previous) if previous else None
    trend = None
    if recent_mean is not None and prev_mean is not None:
        if recent_mean > prev_mean + 2:
            trend = "improving"
        elif recent_mean < prev_mean - 2:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "total_reviews": len(entries),
        "avg_priority_score": avg_score,
        "per_category": per_cat,
        "high_risk_count": high_risk_count,
        "risk_ratio": risk_ratio,
        "recent_trend": trend,
    }


def make_entry(pr_number: str,
               title: str,
               category: str,
               priority_score: int,
               high_risk: bool,
               content_preview: str = "",
               timestamp: str = None,
               extra: dict = None) -> dict:
    """Create a standardized history entry."""
    timestamp = timestamp or _now_iso()
    content_hash = _compute_content_hash(content_preview or "")
    entry = {
        "pr_number": pr_number,
        "title": title,
        "category": category,
        "priority_score": priority_score,
        "high_risk": bool(high_risk),
        "content_hash": content_hash,
        "timestamp": timestamp,
    }
    if extra:
        entry["meta"] = extra
    return entry


def update_history(pr_number: str,
                   title: str,
                   category: str,
                   priority_score: int,
                   high_risk: bool,
                   content_preview: str = "",
                   max_entries: int = MAX_ENTRIES,
                   path: str = HISTORY_PATH,
                   replace_duplicate: bool = True,
                   extra: dict = None) -> dict:
    """
    Load history, add or update an entry, compute metrics, and save.

    Returns the computed metrics for convenience.
    """
    entries = load_history(path)
    content_hash = _compute_content_hash(content_preview or "")

    dup_idx = find_duplicate(entries, pr_number=pr_number, content_hash=content_hash)
    new_entry = make_entry(pr_number, title, category, priority_score, high_risk, content_preview, extra=extra)

    if dup_idx is not None:
        if replace_duplicate:
            entries[dup_idx] = new_entry
            print(f"[INFO] Replaced duplicate history entry at index {dup_idx} (pr={pr_number})")
        else:
            print(f"[INFO] Duplicate detected (pr={pr_number}) — not replaced")
    else:
        entries.append(new_entry)
        print(f"[INFO] Appended new history entry (pr={pr_number})")

    # Trim and save
    entries = trim_history(entries, max_entries)
    save_history(entries, path)

    metrics = compute_metrics(entries)
    try:
        with open(path + ".summary.json", "w", encoding="utf-8") as mf:
            json.dump(metrics, mf, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save metrics snapshot: {e}")

    return metrics


# --- convenience CLI ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review history manager (test CLI).")
    parser.add_argument("--pr", dest="pr", help="PR number", required=False)
    parser.add_argument("--title", dest="title", help="PR title", default="(untitled)")
    parser.add_argument("--category", dest="category", help="PR category", default="general")
    parser.add_argument("--score", dest="score", type=int, help="Priority score", default=50)
    parser.add_argument("--risk", dest="risk", action="store_true", help="Mark as high risk")
    parser.add_argument("--preview", dest="preview", help="Content preview to hash", default="")
    args = parser.parse_args()

    metrics = update_history(
        pr_number=str(args.pr) if args.pr else None,
        title=args.title,
        category=args.category,
        priority_score=args.score,
        high_risk=args.risk,
        content_preview=args.preview,
        max_entries=MAX_ENTRIES,
        path=HISTORY_PATH
    )
    print("[INFO] Updated history metrics:")
    print(json.dumps(metrics, indent=2))
