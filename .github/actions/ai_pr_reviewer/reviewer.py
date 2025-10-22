#!/usr/bin/env python3
"""
Full Research Build: Self-Evaluation + Code Quality Metrics
Replace previous reviewer.py with this file.

Produces additional artifact: ai_self_eval.json
"""

import os
import json
import time
import hashlib
import re
from datetime import datetime
from statistics import mean
import math

# optional third-party imports (ensure installed in workflow)
try:
    import requests
except Exception:
    requests = None

try:
    from openai import OpenAI, APIError, RateLimitError
except Exception:
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception

# ---------------- Config ----------------
HISTORY_PATH = "review_history.json"
ADAPTIVE_LOG_PATH = "ai_adaptive_log.json"
METADATA_PATH = "review_metadata.json"
FEEDBACK_PATH = "ai_review.md"
SELF_EVAL_PATH = "ai_self_eval.json"
MAX_HISTORY = 400
DIFF_PATH = "pr_diff.patch"

# ---------------- Utilities ----------------
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

# ---------------- History & Adaptive ----------------
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

def compute_history_metrics(entries):
    if not entries:
        return {"total_reviews": 0, "avg_priority_score": None, "per_category": {}, "high_risk_count": 0, "risk_ratio": 0.0, "recent_trend": None}
    scores = [e["priority_score"] for e in entries if isinstance(e.get("priority_score"), (int, float))]
    avg_score = round(mean(scores), 2) if scores else None
    per_cat = {}
    for e in entries:
        cat = e.get("category", "uncategorized")
        per_cat[cat] = per_cat.get(cat, 0) + 1
    high_risk_count = sum(1 for e in entries if e.get("high_risk"))
    risk_ratio = round(high_risk_count / len(entries) * 100, 2)
    # trend comparing windows
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
    return {"total_reviews": len(entries), "avg_priority_score": avg_score, "per_category": per_cat, "high_risk_count": high_risk_count, "risk_ratio": risk_ratio, "recent_trend": trend}

def find_history_duplicate(entries, pr_number=None, content_hash=None):
    for i, e in enumerate(entries):
        if pr_number and e.get("pr_number") and str(e.get("pr_number")) == str(pr_number): return i
        if content_hash and e.get("content_hash") == content_hash: return i
    return None

def update_history(pr_number, title, category, priority_score, high_risk, content_preview, extra=None):
    entries = load_history()
    content_hash = compute_hash(content_preview or "")
    dup_idx = find_history_duplicate(entries, pr_number=str(pr_number) if pr_number else None, content_hash=content_hash)
    entry = {"pr_number": str(pr_number) if pr_number else None, "title": title, "category": category,
             "priority_score": priority_score, "high_risk": bool(high_risk), "content_hash": content_hash,
             "timestamp": now_iso(), "meta": extra or {}}
    if dup_idx is not None:
        entries[dup_idx] = entry
        print(f"[INFO] Replaced duplicate history entry (index={dup_idx}, pr={pr_number})")
    else:
        entries.append(entry)
        print(f"[INFO] Appended history entry (pr={pr_number})")
    save_history(entries)
    return compute_history_metrics(entries)

# ---------------- Adaptive Engine ----------------
def load_adaptive_log(path=ADAPTIVE_LOG_PATH):
    data = safe_json_load(path)
    if not isinstance(data, dict): return {"history": [], "average_score": None, "high_risk_count": 0}
    return data

def save_adaptive_log(log, path=ADAPTIVE_LOG_PATH):
    safe_json_save(path, log)

def analyze_adaptive_settings(history_entries):
    if not history_entries:
        return {"tone": "neutral", "depth": "standard", "caution_level": "normal", "trend_summary": "No history."}
    recent = history_entries[-12:]
    scores = [e.get("priority_score", 0) for e in recent if isinstance(e.get("priority_score"), (int, float))]
    avg_score = mean(scores) if scores else 0
    high_risk_count = sum(1 for e in recent if e.get("high_risk"))
    if avg_score < 35 and high_risk_count == 0: tone, depth, caution = "concise", "light", "low"; summary="Low risk trend."
    elif avg_score < 70: tone, depth, caution = "balanced", "standard", "normal"; summary="Moderate risk trend."
    else: tone, depth, caution = "cautious", "deep", "high"; summary="High risk trend — increase scrutiny."
    return {"tone": tone, "depth": depth, "caution_level": caution, "trend_summary": summary, "avg_recent_priority": round(avg_score,2), "recent_high_risk": high_risk_count}

# ---------------- Diff analysis / CQI ----------------
def read_diff(path=DIFF_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        print(f"[INFO] Loaded diff ({len(data)} chars)")
        return data
    except Exception as e:
        print(f"[WARN] couldn't read diff: {e}")
        return ""

def extract_code_quality_metrics(diff_text):
    """
    Heuristic metrics:
      - added_lines_count
      - added_functions_count (defs added)
      - avg_function_length (approx)
      - cyclomatic_proxies (ifs/for/while in added lines)
      - tests_added (presence of tests/pytest)
      - docstring_added (presence of triple quotes in added lines)
    Returns dict + computed Code Quality Index (CQI 0-100).
    """
    if not diff_text:
        return {"cqi": None, "metrics": {}}
    added_lines = [line[1:] for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")]
    deleted_lines = [line[1:] for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")]
    added_text = "\n".join(added_lines)
    added_count = len(added_lines)
    funcs_added = len(re.findall(r"^\s*def\s+\w+\s*\(", added_text, flags=re.MULTILINE))
    # approximate function lengths by counting non-empty lines between defs
    func_lengths = []
    for m in re.finditer(r"(?:^|\n)\s*def\s+\w+\s*\(.*?\):", added_text):
        start = m.start()
        # slice from start to next def or end
        tail = added_text[start:]
        next_def = re.search(r"(?:\n)\s*def\s+\w+\s*\(", tail)
        block = tail[:next_def.start()] if next_def else tail
        func_lengths.append(len([ln for ln in block.splitlines() if ln.strip()]))
    avg_func_len = round(mean(func_lengths),2) if func_lengths else 0
    cyclomatic = sum(len(re.findall(r"\b(if|elif|for|while|case|&&|\|\|)\b", line)) for line in added_lines)
    tests_added = bool(re.search(r"(tests?/|pytest|unittest|def test_)", added_text, flags=re.IGNORECASE))
    docs_added = bool(re.search(r'"""|\'\'\'', added_text))
    # heuristics to map to 0-1
    complexity = min(1.0, cyclomatic / max(1, (added_count/5)))  # normalized
    test_score = 1.0 if tests_added else 0.2
    doc_score = 1.0 if docs_added else 0.3
    func_factor = min(1.0, funcs_added / max(1, (added_count/20)))
    # compute CQI: higher is better
    # idea: good tests/docs raise CQI, high complexity lowers it
    cqi_raw = (0.35 * (1 - complexity)) + (0.35 * test_score) + (0.15 * doc_score) + (0.15 * func_factor)
    cqi = int(max(0, min(100, round(cqi_raw * 100))))
    metrics = {
        "added_lines": added_count,
        "funcs_added": funcs_added,
        "avg_func_length": avg_func_len,
        "cyclomatic_proxy": cyclomatic,
        "tests_added": tests_added,
        "docs_added": docs_added,
        "complexity_norm": round(complexity,3),
        "func_factor": round(func_factor,3)
    }
    return {"cqi": cqi, "metrics": metrics}

# ---------------- Self-Eval of AI feedback ----------------
def evaluate_ai_feedback(ai_markdown, adaptive_tone, diff_text):
    """
    Produces self-eval axes:
      - clarity (readability): sentence length / coherence heuristics
      - actionability: presence of concrete verbs, code examples, test suggestions
      - tone_alignment: match between requested tone and actual phrasing
      - coverage: ratio of issues found vs diff size heuristics
    Returns dict with float scores [0..1] and ai_confidence [0..1]
    """
    text = ai_markdown or ""
    # clarity: shorter average sentence length -> clearer; penalize extremely short
    sentences = re.split(r'[.?!]\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]
    avg_sent_len = mean([len(s.split()) for s in sentences]) if sentences else 0
    clarity = max(0.0, min(1.0, (20 - abs(12 - avg_sent_len)) / 20))  # best avg ~12 words

    # actionability: presence of verbs like "add", "test", "refactor", "use", "avoid", presence of code blocks or recommendations
    action_verbs = len(re.findall(r"\b(add|write|test|refactor|replace|use|ensure|validate|assert|check|fix)\b", text, flags=re.IGNORECASE))
    code_snippets = bool(re.search(r"```|`[^\n`]+`", text))
    actionability = max(0.0, min(1.0, (action_verbs / 6) + (0.2 if code_snippets else 0)))

    # tone_alignment: check for polite/encouraging words vs strict words
    tone = adaptive_tone or "balanced"
    encouraging_words = len(re.findall(r"\b(consider|recommend|suggest|please|nice|good)\b", text, flags=re.IGNORECASE))
    strict_words = len(re.findall(r"\b(must|should not|avoid|critical|fail|error)\b", text, flags=re.IGNORECASE))
    if tone == "concise":
        tone_alignment = max(0.0, min(1.0, (1 - (avg_sent_len/30)) + (0.1 * encouraging_words)))
    elif tone == "cautious":
        tone_alignment = max(0.0, min(1.0, (0.4 * strict_words) + (0.1 * encouraging_words)))
    else:  # balanced/standard
        tone_alignment = max(0.0, min(1.0, 0.5 * (encouraging_words + strict_words + 1) / 5))

    # coverage: heuristics using number of bullets in Potential Issues vs changed lines
    bullets = len(re.findall(r"^- |\n- ", text))
    added_lines = len([l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")])
    if added_lines == 0:
        coverage = 1.0 if bullets > 0 else 0.5
    else:
        ratio = min(1.0, (bullets * 5) / max(1, added_lines))
        coverage = ratio

    # combined confidence (weights tuned for research demo)
    weights = {"clarity": 0.28, "actionability": 0.32, "tone_alignment": 0.2, "coverage": 0.2}
    ai_confidence = (clarity * weights["clarity"] + actionability * weights["actionability"] +
                     tone_alignment * weights["tone_alignment"] + coverage * weights["coverage"])
    # normalize to 0..1
    ai_confidence = max(0.0, min(1.0, ai_confidence))

    return {
        "clarity": round(clarity, 3),
        "actionability": round(actionability, 3),
        "tone_alignment": round(tone_alignment, 3),
        "coverage": round(coverage, 3),
        "ai_confidence": round(ai_confidence, 3),
        "bullets": bullets,
        "added_lines": added_lines,
        "avg_sentence_length": round(avg_sent_len,2)
    }

# ---------------- OpenAI wrapper ----------------
def request_with_retry(client, messages, model="gpt-4o-mini", max_retries=3, timeout=30):
    if client is None:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(model=model, messages=messages, timeout=timeout)
            choice = completion.choices[0]
            if hasattr(choice, "message"):
                return choice.message.content
            return choice.get("message", {}).get("content") or choice.get("text")
        except RateLimitError:
            wait = 5 * attempt
            print(f"[WARN] Rate limit; sleeping {wait}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)
        except APIError as e:
            print(f"[ERROR] OpenAI API error: {e} (attempt {attempt}/{max_retries})")
            time.sleep(3)
        except Exception as e:
            print(f"[FATAL] Unexpected OpenAI error: {e}")
            break
    print("[FAIL] OpenAI request failed after retries.")
    return None

# ---------------- categorize helper ----------------
def categorize_pr(title, body, diff_content):
    text = f"{title} {body} {diff_content}".lower()
    if any(w in text for w in ["fix", "bug", "error", "issue"]): return "bug fix"
    if any(w in text for w in ["add", "feature", "implement", "new"]): return "feature addition"
    if any(w in text for w in ["refactor","cleanup","optimize","performance"]): return "refactor"
    if any(w in text for w in ["doc","readme","typo"]): return "documentation update"
    if any(w in text for w in ["test","pytest","unittest"]): return "test update"
    return "general change"

# ---------------- metadata helper ----------------
def save_metadata(mode, success, path=METADATA_PATH):
    payload = {"mode": mode, "success": bool(success), "timestamp": now_iso(), "feedback_file": FEEDBACK_PATH}
    safe_json_save(path, payload)
    print(f"[INFO] Saved metadata to {path}")

# ---------------- Main ----------------
def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token]):
        print("[FATAL] Missing env vars (GITHUB_REPOSITORY, PR_NUMBER, GITHUB_TOKEN required).")
        return

    print(f"[START] Day 13 — Intelligent Self-Eval Review for {repo} (PR #{pr_number})")
    mode = "LIVE" if (openai_key and OpenAI is not None) else "MOCK"
    print(f"[INFO] Mode: {mode}")

    # fetch PR metadata
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
        print("[WARN] No diff; exiting.")
        save_metadata(mode, success=False)
        return

    # derive adaptive context
    history = load_history()
    adaptive_settings = analyze_adaptive_settings(history)
    adaptive_log = load_adaptive_log()
    adaptive_log.setdefault("history", [])
    # snapshot decision
    decision = {"timestamp": now_iso(), "adaptive_settings": adaptive_settings, "reason": "pre-review snapshot"}
    adaptive_log["history"].append(decision)
    save_adaptive_log(adaptive_log)

    # build prompt (includes adaptive guidance)
    category = categorize_pr(title, body, diff)
    prompt = f"""
You are a senior software engineer performing an adaptive, research-grade code review.

Adaptive context:
- Tone: {adaptive_settings['tone']}
- Depth: {adaptive_settings['depth']}
- Caution: {adaptive_settings['caution_level']}
- Trend: {adaptive_settings['trend_summary']}

PR Title: {title}
PR Description: {body}

--- Begin diff ---
{diff}
--- End diff ---

Produce markdown review with sections:
## AI Code Review Feedback
### Summary
### Potential Issues
### Suggestions
### Testing Recommendations
"""
    client = OpenAI(api_key=openai_key) if (mode == "LIVE" and OpenAI is not None) else None
    ai_feedback = None
    if client:
        ai_feedback = request_with_retry(client, [{"role":"system","content":"You are a senior engineer and code reviewer."},{"role":"user","content":prompt}], model="gpt-4o-mini", max_retries=3)
    else:
        ai_feedback = "## Mock AI Review Feedback\n\n### Summary\n- (mock)\n\n### Potential Issues\n- (mock)\n\n### Suggestions\n- (mock)\n\n### Testing Recommendations\n- (mock)"
    if not ai_feedback:
        print("[WARN] No AI feedback; using fallback.")
        ai_feedback = "## Mock fallback\n\nNo review available."

    # compute CQI
    cqi_obj = extract_code_quality_metrics(diff)
    cqi = cqi_obj.get("cqi")
    cqi_metrics = cqi_obj.get("metrics", {})

    # self-evaluate the feedback
    self_eval = evaluate_ai_feedback(ai_feedback, adaptive_settings.get("tone"), diff)
    # merge with CQI to produce composite 'ai_self_score' (0..1)
    # research weighting: confidence from text + normalized CQI
    cqi_norm = (cqi / 100.0) if cqi is not None else 0.5
    ai_self_score = round((0.75 * self_eval["ai_confidence"] + 0.25 * cqi_norm),3)

    # assemble self-eval payload
    self_eval_payload = {
        "timestamp": now_iso(),
        "clarity": self_eval["clarity"],
        "actionability": self_eval["actionability"],
        "tone_alignment": self_eval["tone_alignment"],
        "coverage": self_eval["coverage"],
        "ai_confidence": self_eval["ai_confidence"],
        "cqi": cqi,
        "cqi_metrics": cqi_metrics,
        "ai_self_score": ai_self_score,
        "notes": "Composite score blends textual self-eval + static CQI heuristics"
    }
    safe_json_save(SELF_EVAL_PATH, self_eval_payload)
    print(f"[INFO] Saved self-eval to {SELF_EVAL_PATH}")

    # append self-eval section to ai_review.md
    try:
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            f.write(ai_feedback)
            f.write("\n\n---\n\n")
            f.write("##  AI Self-Evaluation\n")
            f.write(f"- **AI Confidence:** {self_eval['ai_confidence']}/1.0\n")
            f.write(f"- **AI Self Score:** {ai_self_score}/1.0\n")
            f.write(f"- **Clarity:** {self_eval['clarity']}\n")
            f.write(f"- **Actionability:** {self_eval['actionability']}\n")
            f.write(f"- **Tone alignment:** {self_eval['tone_alignment']}\n")
            f.write(f"- **Coverage:** {self_eval['coverage']}\n")
            f.write(f"- **Code Quality Index (CQI):** {cqi}/100\n")
            f.write("\n_This self-evaluation is generated by the reviewer to calibrate future reviews._\n")
        print(f"[INFO] Appended self-eval to {FEEDBACK_PATH}")
    except Exception as e:
        print(f"[WARN] Could not write ai_review.md: {e}")

    # priority scoring (as before), using analyze heuristics
    # reuse earlier function heuristics (simple)
    bullets = len(re.findall(r"^- |\n- ", ai_feedback))
    base_score = min(100, bullets * 10)
    high_risk_detect = bool(re.search(r"\b(security|vulnerab|data loss|crash|injection|auth|password)\b", ai_feedback, flags=re.IGNORECASE))
    if high_risk_detect:
        base_score = max(80, base_score + 10)
    priority_score = base_score

    # update history and adaptive log
    try:
        metrics = update_history(pr_number, title, category, priority_score, high_risk_detect, diff[:2000], extra={"mode":mode})
        print(f"[INFO] Updated history: total={metrics.get('total_reviews')}, avg_score={metrics.get('avg_priority_score')}")
    except Exception as e:
        print(f"[WARN] update_history failed: {e}")
        
    # --- Reinforcement logging for adaptive learning ---
    try:
        reward_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pr_number": pr_number,
            "priority_score": analysis.get("priority_score", 0),
            "high_risk": analysis.get("high_risk", False),
            "clarity_score": len(ai_feedback) / 500,  # proxy metric for verbosity
            "actionability": analysis.get("issue_count", 0) / 5,  # proxy for actionable suggestions
            "category": category,
            "adaptive_mode": adaptive_context,
        }

        with open("reward_log.json", "a+", encoding="utf-8") as f:
            try:
                f.seek(0)
                logs = json.load(f)
            except:
                logs = []
            logs.append(reward_log)
            f.seek(0)
            json.dump(logs[-100:], f, indent=2)  # keep latest 100
        print("[INFO] Reinforcement log updated.")
    except Exception as e:
        print(f"[WARN] Failed to update reinforcement log: {e}")

    try:
        alog = load_adaptive_log()
        alog.setdefault("history", []).append({"timestamp": now_iso(), "pr": pr_number, "priority_score": priority_score, "ai_self_score": ai_self_score, "high_risk": high_risk_detect})
        # keep last N
        alog["history"] = alog["history"][-500:]
        # update aggregates
        scores = [h.get("ai_self_score") for h in alog["history"] if isinstance(h.get("ai_self_score"), (int, float))]
        alog["average_score"] = round(mean(scores),3) if scores else None
        alog["high_risk_count"] = sum(1 for h in alog["history"] if h.get("high_risk"))
        save_adaptive_log(alog)
        print("[INFO] Adaptive log updated with self-eval metrics.")
    except Exception as e:
        print(f"[WARN] Could not update adaptive log: {e}")

    # adjust adaptive behavior based on ai_self_score
    # simple mapping: low confidence -> increase caution & depth
    adjust_note = ""
    try:
        if ai_self_score < 0.75:
            adjust_note = "Low self-confidence detected -> future runs will increase caution/depth."
            # push a synthetic entry into history to influence analyze_adaptive_settings
            try:
                update_history(pr_number + "_selfcal", title + " (selfcal)", category, max(priority_score, 90), True, "")
            except:
                pass
        elif ai_self_score > 0.92:
            adjust_note = "High self-confidence -> future runs may be more concise."
        else:
            adjust_note = "Self-confidence within normal bounds."
    except Exception as e:
        print(f"[WARN] Adaptive adjustment failed: {e}")

    # save metadata
    save_metadata(mode, success=True)

    # try to post comment to PR with review + self-eval summary (best-effort)
    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    try:
        comment_body = {
            "body": f"### Adaptive AI PR Review \n\n{ai_feedback}\n\n**Priority Score:** {priority_score}/100\n**AI Self Score:** {ai_self_score}/1.0\n**CQI:** {cqi}/100\n\n*{adjust_note}*"
        }
        resp = requests.post(comment_url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, json=comment_body, timeout=15)
        if resp.status_code == 201:
            print("[SUCCESS] Posted comment to PR.")
        else:
            print(f"[WARN] Could not post PR comment: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[WARN] Exception posting PR comment: {e}")

    print("[SUMMARY] Day 13 run complete. Artifacts: ai_review.md, review_metadata.json, review_history.json, ai_adaptive_log.json, ai_self_eval.json")

if __name__ == "__main__":
    main()


















