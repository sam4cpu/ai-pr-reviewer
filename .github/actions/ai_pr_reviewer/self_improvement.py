"""
Self-Improvement Cycle (self_improvement.py)

- Reads review_history.json and ai_adaptive_log.json
- Computes meta metrics and trends
- Generates an improvement_plan.json + quality_report.md
- Uses OpenAI when available (with retry/backoff), falls back to heuristics otherwise
- Saves self_improvement_metrics.json for diagnostics
- Best-effort posts a short summary comment to the PR (if GITHUB env vars present)
"""

import os
import json
import time
import math
import statistics
from datetime import datetime

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

# Files
HISTORY_PATH = "review_history.json"
ADAPTIVE_PATH = "ai_adaptive_log.json"
IMPROVEMENT_PLAN = "improvement_plan.json"
QUALITY_REPORT = "quality_report.md"
METRICS_OUT = "self_improvement_metrics.json"

# Config
MAX_HISTORY_WINDOW = 100  # how many recent entries to consider
OPENAI_MODEL = "gpt-4o-mini"  # consult your usage & quotas
OPENAI_RETRIES = 3
OPENAI_TIMEOUT = 30


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def safe_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def safe_save(path, obj):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[WARN] failed to save {path}: {e}")
        return False


def save_text(path, txt):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        return True
    except Exception as e:
        print(f"[WARN] failed to write {path}: {e}")
        return False


# -------------------------
# Metric helpers
# -------------------------
def aggregate_history_metrics(history):
    """
    Expect history: list of entries with keys:
      - priority_score (0..100)
      - high_risk (bool)
      - category
      - meta (may include cqi or other)
    Returns aggregated metrics dict.
    """
    if not history:
        return {
            "total_reviews": 0,
            "avg_priority": None,
            "median_priority": None,
            "high_risk_count": 0,
            "high_risk_ratio": 0.0,
            "per_category": {},
            "avg_cqi": None,
            "recent_trend": None
        }

    window = history[-MAX_HISTORY_WINDOW:]
    scores = [e.get("priority_score", 0) for e in window if isinstance(e.get("priority_score"), (int, float))]
    avg_priority = round(statistics.mean(scores), 2) if scores else None
    median_priority = round(statistics.median(scores), 2) if scores else None
    high_risk_count = sum(1 for e in window if e.get("high_risk"))
    high_risk_ratio = round((high_risk_count / len(window)) * 100, 2)
    per_cat = {}
    for e in window:
        cat = e.get("category", "uncategorized")
        per_cat[cat] = per_cat.get(cat, 0) + 1

    # avg CQI if available in meta
    cqi_vals = []
    for e in window:
        meta = e.get("meta", {}) or {}
        cqi = meta.get("cqi") or e.get("meta", {}).get("cqi") or None
        if isinstance(cqi, (int, float)):
            cqi_vals.append(cqi)
    avg_cqi = round(statistics.mean(cqi_vals), 2) if cqi_vals else None

    # simple trend: compare average of last 10 vs previous 10
    def window_mean(lst, n):
        if len(lst) < n: return None
        return statistics.mean(lst[-n:])

    recent_n = 10
    recent_avg = window_mean(scores, recent_n)
    prev_avg = statistics.mean(scores[-2*recent_n:-recent_n]) if len(scores) >= 2*recent_n else None
    trend = None
    if recent_avg is not None and prev_avg is not None:
        if recent_avg > prev_avg + 2:
            trend = "worse (more priority issues)"
        elif recent_avg < prev_avg - 2:
            trend = "improving"
        else:
            trend = "stable"

    return {
        "total_reviews": len(window),
        "avg_priority": avg_priority,
        "median_priority": median_priority,
        "high_risk_count": high_risk_count,
        "high_risk_ratio": high_risk_ratio,
        "per_category": per_cat,
        "avg_cqi": avg_cqi,
        "recent_trend": trend
    }


def aggregate_adaptive_metrics(adaptive_log):
    """
    adaptive_log expected with a 'history' list of entries possibly containing:
      - ai_self_score
      - priority_score
      - high_risk
    """
    history = adaptive_log.get("history", []) if isinstance(adaptive_log, dict) else []
    if not history:
        return {"avg_ai_self_score": None, "ai_self_count": 0, "recent_high_risk": 0}
    scores = [h.get("ai_self_score") for h in history if isinstance(h.get("ai_self_score"), (int, float))]
    avg_ai = round(statistics.mean(scores), 3) if scores else None
    recent_high_risk = sum(1 for h in history[-MAX_HISTORY_WINDOW:] if h.get("high_risk"))
    return {"avg_ai_self_score": avg_ai, "ai_self_count": len(history), "recent_high_risk": recent_high_risk}


# -------------------------
# OpenAI helper
# -------------------------
def run_openai(client, messages, model=OPENAI_MODEL, max_retries=OPENAI_RETRIES):
    if client is None:
        return None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(model=model, messages=messages, timeout=OPENAI_TIMEOUT)
            choice = resp.choices[0]
            # prefer message.content shape
            if hasattr(choice, "message"):
                return choice.message.content
            return choice.get("message", {}).get("content") or choice.get("text")
        except RateLimitError:
            wait = 5 * attempt
            print(f"[WARN] OpenAI rate limit; sleeping {wait}s (attempt {attempt})")
            time.sleep(wait)
        except APIError as e:
            print(f"[WARN] OpenAI APIError: {e} (attempt {attempt})")
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] OpenAI failure: {e}")
            break
    print("[FAIL] OpenAI calls failed after retries.")
    return None


# -------------------------
# Heuristic improvement plan generator (fallback)
# -------------------------
def heuristic_improvement_plan(metrics, adaptive_summary):
    """
    Create a conservative improvement plan based on numeric metrics.
    Returns dict describing focus areas and recommended actions.
    """
    plan = {"generated_at": now_iso(), "focus_next": [], "avoid_next": [], "learning_summary": "", "actions": []}

    # Use high-risk frequency and avg priority to choose focus areas
    avg_priority = metrics.get("avg_priority") or 0
    high_risk_ratio = metrics.get("high_risk_ratio") or 0
    avg_cqi = metrics.get("avg_cqi")

    if high_risk_ratio > 10 or (avg_priority and avg_priority >= 70):
        plan["focus_next"].append("security & correctness")
        plan["actions"].append("Require explicit security checks and input validation guidance in reviews.")
    if avg_cqi is not None and avg_cqi < 60:
        plan["focus_next"].append("test coverage & documentation")
        plan["actions"].append("Emphasize tests and docstrings; suggest pytest cases where missing.")
    if metrics.get("per_category", {}).get("feature addition", 0) > metrics.get("per_category", {}).get("bug fix", 0):
        plan["focus_next"].append("API design & backwards compatibility")
        plan["actions"].append("Check API changes, deprecations, and version compatibility.")
    if avg_priority and avg_priority < 30:
        plan["focus_next"].append("conciseness")
        plan["actions"].append("Favor concise, high-signal feedback; reduce boilerplate comments.")

    # default guidance
    if not plan["focus_next"]:
        plan["focus_next"].append("balanced coverage")
        plan["actions"].append("Maintain balanced checks: tests, docs, performance, security.")

    plan["avoid_next"].append("overly generic bullet lists without test suggestions")
    plan["learning_summary"] = f"Adaptive summary: {adaptive_summary.get('trend_summary', 'none')}"
    return plan


# -------------------------
# Compose OpenAI prompt (for improvement plan + quality report)
# -------------------------
def build_openai_prompt(metrics, adaptive_summary, recent_samples_text):
    prompt = f"""You are an AI engineer that supervises another AI code reviewer. You have the following aggregated metrics from the last reviews:

- Total reviews considered: {metrics.get('total_reviews')}
- Average priority score: {metrics.get('avg_priority')}
- Median priority: {metrics.get('median_priority')}
- High-risk ratio (%): {metrics.get('high_risk_ratio')}
- Average CQI: {metrics.get('avg_cqi')}
- Per-category counts: {metrics.get('per_category')}
- Recent trend: {metrics.get('recent_trend')}

Adaptive summary:
- {adaptive_summary.get('trend_summary', '')}
- Average self-eval score: {adaptive_summary.get('avg_ai_self_score')}

Recent sample snippets (for context):
{recent_samples_text}

Task:
1) Produce an actionable "Improvement Plan" (short JSON-style bullets) that tells the reviewer what to focus on in the next N reviews (N~20). Prioritize security & tests if high-risk trend found. Provide 4-6 concrete actions.
2) Produce a "Quality Report" (concise markdown) summarizing strengths, weaknesses, and a small recommended checklist to validate changes quickly.
3) At the end, output a short "calibration rule" that maps ai_self_score -> suggested tone adjustment, e.g. "<0.75 => cautious/deep", "0.75-0.92 => balanced", ">0.92 => concise".

Format:
Return a JSON object with keys: improvement_plan (object), quality_report (markdown string), calibration (object).

Be concise but actionable.
"""
    return prompt


# -------------------------
# Runner
# -------------------------
def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")  # this job may run after PR + may not have a PR in context
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    print(f"[START] Self-improvement run at {now_iso()} (repo={repo}, pr={pr_number})")

    history = safe_load(HISTORY_PATH) or []
    adaptive = safe_load(ADAPTIVE_PATH) or {}

    metrics = aggregate_history_metrics(history)
    adaptive_metrics = aggregate_adaptive_metrics(adaptive)

    # Prepare recent samples for prompt: take short excerpts from last few reviews 
    recent_texts = []
    for entry in (history[-6:] if len(history) > 0 else []):
        # include title + small preview if available
        txt = (entry.get("title") or "") + " | " + str(entry.get("meta", {}).get("cqi", "")) + " | score:" + str(entry.get("priority_score"))
        recent_texts.append(txt)
    recent_samples_text = "\n".join(recent_texts) or "No recent textual samples available."

    # Build metrics object to save
    out_metrics = {
        "timestamp": now_iso(),
        "history_metrics": metrics,
        "adaptive_metrics": adaptive_metrics
    }
    safe_save(METRICS_OUT, out_metrics)
    print(f"[INFO] Wrote metrics summary to {METRICS_OUT}")

    # Attempt OpenAI plan generation if API key present
    improvement_plan = None
    quality_report_md = None
    calibration = None

    if openai_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=openai_key)
            prompt = build_openai_prompt(metrics, {"trend_summary": adaptive.get("trend_summary", ""), "avg_ai_self_score": adaptive_metrics.get("avg_ai_self_score")}, recent_samples_text)
            messages = [
                {"role": "system", "content": "You are an expert engineering manager producing actionable improvement plans and quality reports for an AI reviewer."},
                {"role": "user", "content": prompt}
            ]
            print("[INFO] Sending prompt to OpenAI for improvement plan generation...")
            raw = run_openai(client, messages)
            if raw:
                try:
                    # Some models output stray text before JSON, try to find first '{'
                    json_start = raw.find("{")
                    json_text = raw[json_start:] if json_start != -1 else raw
                    parsed = json.loads(json_text)
                    improvement_plan = parsed.get("improvement_plan") or parsed.get("improvementPlan") or parsed.get("plan")
                    quality_report_md = parsed.get("quality_report") or parsed.get("quality_report_md") or parsed.get("qualityReport")
                    calibration = parsed.get("calibration")
                except Exception:
                    # if parsing failed, wrap raw into a markdown quality report and fallback to heuristics for plan
                    quality_report_md = "## Generated Quality Report (raw)\n\n" + raw
                    improvement_plan = heuristic_improvement_plan(metrics, {"trend_summary": adaptive.get("trend_summary", "")})
                    calibration = {
                        "rules": {
                            "<0.75": "increase caution; deep reviews",
                            "0.75-0.92": "balanced reviews",
                            ">0.92": "allow concise reviews"
                        }
                    }
            else:
                print("[WARN] OpenAI returned no content; falling back to heuristic plan.")
                improvement_plan = heuristic_improvement_plan(metrics, {"trend_summary": adaptive.get("trend_summary", "")})
                quality_report_md = f"## Heuristic Quality Report\n\nNo model output; used heuristics.\n\nMetrics snapshot: {metrics}"
                calibration = {"rules": {"<0.75": "cautious", "0.75-0.92": "balanced", ">0.92": "concise"}}
        except Exception as e:
            print(f"[WARN] OpenAI generation failed: {e}; falling back to heuristics.")
            improvement_plan = heuristic_improvement_plan(metrics, {"trend_summary": adaptive.get("trend_summary", "")})
            quality_report_md = f"## Heuristic Quality Report\n\nOpenAI error: {e}\n\nMetrics snapshot: {metrics}"
            calibration = {"rules": {"<0.75": "cautious", "0.75-0.92": "balanced", ">0.92": "concise"}}
    else:
        print("[INFO] No OpenAI key or client; using heuristic improvement plan.")
        improvement_plan = heuristic_improvement_plan(metrics, {"trend_summary": adaptive.get("trend_summary", "")})
        quality_report_md = f"## Heuristic Quality Report\n\nGenerated by heuristics.\n\nMetrics snapshot:\n\n{json.dumps(metrics, indent=2)}"
        calibration = {"rules": {"<0.75": "cautious", "0.75-0.92": "balanced", ">0.92": "concise"}}

    # Save improvement plan and quality report
    plan_payload = {
        "generated_at": now_iso(),
        "improvement_plan": improvement_plan,
        "calibration": calibration,
        "metrics": metrics,
        "adaptive_summary": {"avg_ai_self_score": adaptive_metrics.get("avg_ai_self_score"), "recent_trend": metrics.get("recent_trend")}
    }
    saved = safe_save(IMPROVEMENT_PLAN, plan_payload)
    if saved:
        print(f"[INFO] Saved improvement plan -> {IMPROVEMENT_PLAN}")
    save_text(QUALITY_REPORT, quality_report_md or "No quality report generated.")
    print(f"[INFO] Saved quality report -> {QUALITY_REPORT}")

    # Optionally post a short summary to PR (if environment has a PR context and token)
    if token and repo and pr_number:
        try:
            short_summary = f"AI Self-Improvement Plan generated. Key focuses: {', '.join(improvement_plan.get('focus_next')[:3]) if improvement_plan else 'n/a'}; trend: {metrics.get('recent_trend')}"
            comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
            payload = {"body": f"### AI Self-Improvement Summary\n\n{short_summary}\n\nSee `{IMPROVEMENT_PLAN}` and `{QUALITY_REPORT}` artifacts."}
            resp = requests.post(comment_url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, json=payload, timeout=15)
            if resp is not None and resp.status_code == 201:
                print("[SUCCESS] Posted self-improvement summary to PR.")
            else:
                status = resp.status_code if resp is not None else "no-response"
                txt = resp.text if resp is not None else ""
                print(f"[WARN] Could not post PR comment: {status} {txt}")
        except Exception as e:
            print(f"[WARN] Exception posting PR comment: {e}")

    print("[SUMMARY] Self-improvement run complete.")
    return 0


if __name__ == "__main__":
    main()
