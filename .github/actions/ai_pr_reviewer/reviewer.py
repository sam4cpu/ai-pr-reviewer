"""
Day 12: Full self-contained adaptive AI PR reviewer (reviewer.py)

- Adaptive memory: review_history.json
- Adaptive log: ai_adaptive_log.json
- Priority scoring & risk detection
- OpenAI integration with retry/backoff + mock fallback
- Posts PR comment (uses GITHUB_TOKEN)
- Saves artifacts: ai_review.md, review_metadata.json, review_history.json, ai_adaptive_log.json
"""

import os
import json
import time
import hashlib
import re
from datetime import datetime
from statistics import mean

# Attempt to import OpenAI client; handle if missing in runner
try:
    from openai import OpenAI, APIError, RateLimitError
except Exception:
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception

HISTORY_PATH = "review_history.json"
ADAPTIVE_LOG_PATH = "ai_adaptive_log.json"
METADATA_PATH = "review_metadata.json"
FEEDBACK_PATH = "ai_review.md"
MAX_HISTORY = 200
DIFF_PATH = "pr_diff.patch"

# Utilities
def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def safe_json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def safe_json_save(path, obj):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[WARN] Failed to save {path}: {e}")

def compute_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

# History management
def load_history(path=HISTORY_PATH):
    data = safe_json_load(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    return []

def save_history(entries, path=HISTORY_PATH):
    entries = entries[-MAX_HISTORY:]
    safe_json_save(path, entries)
   
    try:
        metrics = compute_history_metrics(entries)
        safe_json_save(path + ".summary.json", metrics)
    except Exception:
        pass

def find_history_duplicate(entries, pr_number=None, content_hash=None):
    for i, e in enumerate(entries):
        if pr_number and e.get("pr_number") and str(e.get("pr_number")) == str(pr_number):
            return i
        if content_hash and e.get("content_hash") == content_hash:
            return i
    return None

def compute_history_metrics(entries):
    if not entries:
        return {
            "total_reviews": 0,
            "avg_priority_score": None,
            "per_category": {},
            "high_risk_count": 0,
            "risk_ratio": 0.0,
            "recent_trend": None
        }
    scores = [e["priority_score"] for e in entries if isinstance(e.get("priority_score"), (int, float))]
    avg_score = round(mean(scores),2) if scores else None
    per_cat = {}
    for e in entries:
        cat = e.get("category", "uncategorized")
        per_cat[cat] = per_cat.get(cat, 0) + 1
    high_risk_count = sum(1 for e in entries if e.get("high_risk"))
    risk_ratio = round(high_risk_count / len(entries) * 100, 2)
    # simple trend: compare last window to previous
    window = 8
    recent = [e.get("priority_score") for e in entries[-window:] if isinstance(e.get("priority_score"), (int, float))]
    prev = [e.get("priority_score") for e in entries[-2*window:-window] if isinstance(e.get("priority_score"), (int, float))]
    trend = None
    if recent and prev:
        if mean(recent) > mean(prev) + 2:
            trend = "improving"
        elif mean(recent) < mean(prev) - 2:
            trend = "declining"
        else:
            trend = "stable"
    return {
        "total_reviews": len(entries),
        "avg_priority_score": avg_score,
        "per_category": per_cat,
        "high_risk_count": high_risk_count,
        "risk_ratio": risk_ratio,
        "recent_trend": trend
    }

def update_history(pr_number, title, category, priority_score, high_risk, content_preview, extra=None):
    entries = load_history()
    content_hash = compute_hash(content_preview or "")
    dup_idx = find_history_duplicate(entries, pr_number=str(pr_number) if pr_number else None, content_hash=content_hash)
    entry = {
        "pr_number": str(pr_number) if pr_number else None,
        "title": title,
        "category": category,
        "priority_score": priority_score,
        "high_risk": bool(high_risk),
        "content_hash": content_hash,
        "timestamp": now_iso(),
        "meta": extra or {}
    }
    if dup_idx is not None:
        entries[dup_idx] = entry
        print(f"[INFO] Replaced duplicate history entry at index {dup_idx} (pr={pr_number})")
    else:
        entries.append(entry)
        print(f"[INFO] Appended new history entry (pr={pr_number})")
    save_history(entries)
    return compute_history_metrics(entries)

# -------------------------
# Adaptive engine (self-contained)
# -------------------------
def load_adaptive_log(path=ADAPTIVE_LOG_PATH):
    data = safe_json_load(path)
    if not isinstance(data, dict):
        return {"history": [], "average_score": 0.0, "high_risk_count": 0}
    return data

def save_adaptive_log(log, path=ADAPTIVE_LOG_PATH):
    safe_json_save(path, log)

def analyze_adaptive_settings(history_entries):
    """
    Decide tone/depth/caution level using recent entries.
    Returns a dict with tone, depth, caution_level, trend_summary.
    """
    if not history_entries:
        return {
            "tone": "neutral",
            "depth": "standard",
            "caution_level": "normal",
            "trend_summary": "No historical data available."
        }
    recent = history_entries[-10:]
    scores = [e.get("priority_score", 0) for e in recent if isinstance(e.get("priority_score"), (int, float))]
    high_risk_count = sum(1 for e in recent if e.get("high_risk"))
    avg_score = mean(scores) if scores else 0

    if avg_score < 35 and high_risk_count == 0:
        tone, depth, caution = "concise", "light", "low"
        summary = "Recent PRs are low-risk. Keep reviews concise."
    elif avg_score < 70:
        tone, depth, caution = "balanced", "standard", "normal"
        summary = "Moderate risk. Maintain balanced analysis."
    else:
        tone, depth, caution = "cautious", "deep", "high"
        summary = "High-risk trend detected. Emphasize correctness and security."

    return {
        "tone": tone,
        "depth": depth,
        "caution_level": caution,
        "trend_summary": summary,
        "avg_recent_priority": round(avg_score,2),
        "recent_high_risk": high_risk_count
    }

# OpenAI and text helpers
def read_diff(path=DIFF_PATH):
    if not os.path.exists(path):
        print("[WARN] No diff file found.")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        print(f"[INFO] Loaded diff file ({len(data)} characters).")
        return data[:12000]
    except Exception as e:
        print(f"[WARN] Could not read diff: {e}")
        return None

def analyze_feedback_priority(ai_feedback: str):
    """Score feedback and detect high-risk keywords."""
    text = (ai_feedback or "").lower()
    risk_terms = ["security", "vulnerability", "data loss", "crash", "injection", "auth", "password", "corrupt", "race"]
    high_risk = any(t in text for t in risk_terms)
    bullets = len(re.findall(r"^- ", ai_feedback, flags=re.MULTILINE)) + len(re.findall(r"- ", ai_feedback))
    # heuristic: each bullet ~10 points
    base = min(100, bullets * 10)
    if high_risk:
        base = max(80, base + 10)
    return {"issue_count": bullets, "high_risk": high_risk, "priority_score": base}

def request_with_retry(client, messages, model="gpt-4o-mini", max_retries=3, timeout=30):
    if client is None:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=timeout
            )
            # support both streaming and standard response shape
            choice = completion.choices[0]
            if hasattr(choice, "message"):
                return choice.message.content
            # fallback if older response shape
            return choice.get("message", {}).get("content") or choice.get("text")
        except RateLimitError:
            wait = 5 * attempt
            print(f"[WARN] Rate limit; sleeping {wait}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)
        except APIError as e:
            print(f"[ERROR] OpenAI API error: {e} (attempt {attempt}/{max_retries})")
            time.sleep(3)
        except Exception as e:
            print(f"[FATAL] Unexpected error contacting OpenAI: {e}")
            break
    print("[FAIL] OpenAI request failed after retries.")
    return None

# -------------------------
# Save metadata helper
# -------------------------
def save_metadata(mode, success, path=METADATA_PATH):
    payload = {
        "mode": mode,
        "success": bool(success),
        "timestamp": now_iso(),
        "feedback_file": FEEDBACK_PATH
    }
    safe_json_save(path, payload)
    print(f"[INFO] Saved metadata to {path}")

# -------------------------
# Main
# -------------------------
def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token]):
        print("[FATAL] Missing environment variables (GITHUB_REPOSITORY, PR_NUMBER, GITHUB_TOKEN required).")
        return

    print(f"[START] Running Adaptive AI PR Review for {repo} (PR #{pr_number})")
    mode = "LIVE" if openai_key and OpenAI is not None else "MOCK"
    print(f"[INFO] Mode: {mode}")

    # fetch PR data
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    try:
        pr_resp = requests.get(pr_url, headers=headers, timeout=15)
        pr_data = pr_resp.json() if pr_resp.ok else {}
    except Exception as e:
        print(f"[ERROR] Failed to fetch PR data: {e}")
        pr_data = {}
    title = pr_data.get("title", "")
    body = pr_data.get("body", "")

    # read diff
    diff = read_diff()
    if not diff:
        print("[WARN] No diff to analyze, exiting early.")
        save_metadata(mode, success=False)
        return

    # load history and derive adaptive settings
    history = load_history()
    adaptive_settings = analyze_adaptive_settings(history)
    # update adaptive log snapshot
    adaptive_log = load_adaptive_log()
    # keep a brief snapshot in the adaptive log top-level
    adaptive_log.setdefault("history", [])
    adaptive_log.setdefault("average_score", None)
    adaptive_log.setdefault("high_risk_count", 0)

    # record the adaptive decision moment (not the review yet)
    decision = {
        "timestamp": now_iso(),
        "reason": "computed before review",
        "adaptive_settings": adaptive_settings
    }
    adaptive_log["history"].append(decision)
    adaptive_log["average_score"] = adaptive_settings.get("avg_recent_priority")
    adaptive_log["high_risk_count"] = adaptive_settings.get("recent_high_risk", 0)
    save_adaptive_log(adaptive_log)

    # build prompt - include adaptive guidance
    category = categorize_pr(title, body, diff)
    print(f"[INFO] PR category detected: {category}")
    prompt = f"""
You are a senior software engineer performing an adaptive AI code review.

Adaptive context:
- Tone: {adaptive_settings['tone']}
- Depth: {adaptive_settings['depth']}
- Caution: {adaptive_settings['caution_level']}
- Trend: {adaptive_settings['trend_summary']}

You are reviewing a {category} pull request.

PR Title: {title}
PR Description: {body}

Repository context is provided if available; prioritize correctness, readability, tests, and security based on the adaptive context.

--- Begin diff ---
{diff}
--- End diff ---

Provide structured markdown feedback with these sections:

## AI Code Review Feedback

### Summary
- One-paragraph summary of changes.

### Potential Issues
- Bullet list of possible bugs, logic errors, design issues, or risks.

### Suggestions
- Actionable suggestions and refactors.

### Testing Recommendations
- Concrete pytest-style test scenarios to add.
"""

    print("[INFO] Prepared prompt; contacting OpenAI..." if mode == "LIVE" else "[INFO] Prepared prompt; running in MOCK mode.")

    client = OpenAI(api_key=openai_key) if (mode == "LIVE" and OpenAI is not None) else None
    ai_feedback = None
    if client:
        ai_feedback = request_with_retry(client, [
            {"role": "system", "content": "You are a professional software engineer and code reviewer."},
            {"role": "user", "content": prompt}
        ], model="gpt-4o-mini", max_retries=3)
    else:
        # MOCK fallback
        ai_feedback = f"""## Mock AI Review Feedback

### Summary
- (mock) This PR updates files; run with OpenAI key for live feedback.

### Potential Issues
- (mock) No live analysis performed.

### Suggestions
- (mock) Add tests, linting, and CI checks.

### Testing Recommendations
- (mock) Add pytest cases for new functionality.
"""

    if not ai_feedback:
        print("[WARN] No AI feedback returned; using fallback mock text.")
        ai_feedback = "## Mock fallback\n\nNo feedback available."

    # write feedback file
    try:
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            f.write(ai_feedback)
        print(f"[INFO] Saved AI feedback to {FEEDBACK_PATH}")
    except Exception as e:
        print(f"[WARN] Failed to save feedback file: {e}")

    # priority analysis
    analysis = analyze_feedback_priority(ai_feedback)
    print(f"[INFO] Priority score: {analysis['priority_score']}/100 (high_risk={analysis['high_risk']})")

    # update history (dedupe by PR number & content hash)
    try:
        metrics = update_history(
            pr_number=pr_number,
            title=title,
            category=category,
            priority_score=analysis.get("priority_score", 0),
            high_risk=analysis.get("high_risk", False),
            content_preview=diff[:1000],
            extra={"mode": mode, "adaptive_tone": adaptive_settings['tone']}
        )
        print(f"[INFO] Updated history: total={metrics.get('total_reviews')}, avg_score={metrics.get('avg_priority_score')}")
    except Exception as e:
        print(f"[WARN] update_history failed: {e}")

    # append to adaptive log the result of this run
    try:
        run_entry = {
            "timestamp": now_iso(),
            "pr_number": pr_number,
            "priority_score": analysis.get("priority_score"),
            "high_risk": analysis.get("high_risk"),
            "category": category,
            "adaptive_settings": adaptive_settings
        }
        adaptive_log = load_adaptive_log()
        adaptive_log.setdefault("history", []).append(run_entry)
        # maintain last N entries for the adaptive log
        adaptive_log["history"] = adaptive_log["history"][-400:]
        # update simple aggregates
        scores = [h.get("priority_score") for h in adaptive_log["history"] if isinstance(h.get("priority_score"), (int, float))]
        adaptive_log["average_score"] = round(mean(scores),2) if scores else None
        adaptive_log["high_risk_count"] = sum(1 for h in adaptive_log["history"] if h.get("high_risk"))
        save_adaptive_log(adaptive_log)
    except Exception as e:
        print(f"[WARN] Failed to update adaptive log: {e}")

    # Save metadata
    save_metadata(mode, success=True)

    # Post comment on PR (best-effort)
    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    try:
        comment_body = {
            "body": f"### Adaptive AI PR Review\n\n{ai_feedback}\n\n**Priority Score:** {analysis.get('priority_score')}/100\n**Adaptive Tone:** {adaptive_settings['tone']} — {adaptive_settings['trend_summary']}"
        }
        resp = requests.post(comment_url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, json=comment_body, timeout=15)
        if resp.status_code == 201:
            print("[SUCCESS] Posted AI review comment to PR.")
        else:
            print(f"[WARN] Could not post PR comment: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[WARN] Exception posting PR comment: {e}")

    print("[SUMMARY] Run complete. Artifacts: ai_review.md, review_metadata.json, review_history.json, ai_adaptive_log.json")

if __name__ == "__main__":
    main()



















