import os
import requests
import time
import json
import re
from datetime import datetime
from openai import OpenAI, APIError, RateLimitError

def analyze_feedback_priority(ai_feedback: str) -> dict:
    """Extract priority score and detect critical issues."""
    feedback_lower = ai_feedback.lower()

    critical_keywords = [
        "security", "vulnerability", "data loss",
        "crash", "injection", "auth", "password"
    ]
    high_risk_detected = any(k in feedback_lower for k in critical_keywords)

    # Count bullet points
    issue_count = len(re.findall(r"- ", ai_feedback))
    base_score = min(100, issue_count * 10)
    if high_risk_detected:
        base_score = max(80, base_score + 20)

    return {
        "issue_count": issue_count,
        "high_risk": high_risk_detected,
        "priority_score": base_score
    }


def request_with_retry(client, messages, model="gpt-4o-mini", max_retries=3):
    """Handle transient API errors and retry with exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=30
            )
            return completion.choices[0].message.content
        except RateLimitError:
            wait_time = 5 * attempt
            print(f"[WARN] Rate limit hit. Retrying in {wait_time}s...")
            time.sleep(wait_time)
        except APIError as e:
            print(f"[ERROR] API error: {e}. Retrying...")
            time.sleep(3)
        except Exception as e:
            print(f"[FATAL] Unexpected error: {e}")
            break
    print("[FAIL] OpenAI request failed after multiple attempts.")
    return None


def read_diff_file(path="pr_diff.patch"):
    """Read the diff generated for the PR."""
    if not os.path.exists(path):
        print("[WARN] No diff file found.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        diff = f.read()
    print(f"[INFO] Loaded diff file ({len(diff)} characters).")
    return diff[:8000]


def gather_repo_context(base_path="."):
    """Collect key contextual files (README, tests, dependencies)."""
    important_files = ["README.md", "requirements.txt", "pyproject.toml"]
    context_snippets = []

    for file in important_files:
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()[:2000]
            context_snippets.append(f"### {file}\n{content}")

    test_dir = os.path.join(base_path, "tests")
    if os.path.isdir(test_dir):
        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.endswith(".py"):
                    test_path = os.path.join(root, file)
                    with open(test_path, "r", encoding="utf-8") as f:
                        content = f.read()[:1000]
                    context_snippets.append(f"### {test_path}\n{content}")

    print(f"[INFO] Loaded context from {len(context_snippets)} files." if context_snippets else "[INFO] No contextual files found.")
    return "\n\n".join(context_snippets)


def save_metadata(mode, success, feedback_path="ai_review.md"):
    """Save metadata summary for audit/debug."""
    metadata = {
        "mode": mode,
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "feedback_file": feedback_path
    }
    with open("review_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print("[INFO] Metadata saved to review_metadata.json")


def categorize_pr(title, body, diff_content):
    """Categorize PRs to tailor AI feedback."""
    text = f"{title} {body} {diff_content[:500]}".lower()

    if any(word in text for word in ["fix", "bug", "error", "issue"]):
        return "bug fix"
    elif any(word in text for word in ["add", "feature", "implement", "new"]):
        return "feature addition"
    elif any(word in text for word in ["refactor", "cleanup", "optimize"]):
        return "refactor"
    elif any(word in text for word in ["doc", "readme", "typo"]):
        return "documentation update"
    elif any(word in text for word in ["test", "pytest", "unittest"]):
        return "test update"
    else:
        return "general change"

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token]):
        print("[FATAL] Missing one or more required environment variables.")
        return

    print(f"[START] Running AI PR Review for {repo} (PR #{pr_number})...")

    mode = "LIVE" if openai_key else "MOCK"
    print(f"[INFO] Mode: {mode}")

    # --- Fetch PR metadata ---
    headers = {"Authorization": f"Bearer {token}"}
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_data = requests.get(pr_url, headers=headers).json()
    title = pr_data.get("title", "")
    body = pr_data.get("body", "")
    print(f"[INFO] Fetched PR: {title}")

    # --- Load diff and context ---
    diff_content = read_diff_file()
    if not diff_content:
        print("[WARN] No diff to analyze, exiting.")
        save_metadata(mode, success=False)
        return

    category = categorize_pr(title, body, diff_content)
    repo_context = gather_repo_context()
    client = OpenAI(api_key=openai_key) if openai_key else None

    # --- Build AI Prompt ---
    prompt = f"""
You are a senior software engineer reviewing a **{category}** pull request.

**PR Title:** {title}
**Description:** {body}

### Repository Context
{repo_context}

### Code Diff
{diff_content}

Provide structured markdown feedback considering both
the code diff and overall repository context.

## AI Code Review Feedback

### Summary
- Summarize what this PR changes.

### Potential Issues
- List possible bugs, logic errors, or risky design choices.

### Suggestions
- Suggest improvements or refactors.

### Testing Recommendations
- Recommend relevant pytest tests or edge cases.
"""

    print("[INFO] Sending diff + repo context to OpenAI for analysis...")

    # --- Run Review ---
    try:
        ai_feedback = None

        if client:
            ai_feedback = request_with_retry(client, [
                {"role": "system", "content": "You are a professional software engineer reviewing code."},
                {"role": "user", "content": prompt}
            ])
        else:
            print("[INFO] Skipping OpenAI API call (mock mode enabled).")

        if not ai_feedback:
            print("[INFO] Falling back to mock AI feedback mode.")
            ai_feedback = """
## Mock AI Review Feedback

### Summary
- Simulated PR review completed successfully (mock mode).

### Potential Issues
- None detected (test simulation only).

### Suggestions
- Integrate a live OpenAI API key for production reviews.
- Consider adding linting and test coverage steps.

### Testing Recommendations
- Validate workflow triggers and artifact outputs.
- Verify retry logic and mock handling.
"""

        # --- Output and Post ---
        print("\n[OUTPUT] AI Review Feedback:\n")
        print(ai_feedback)

        analysis = analyze_feedback_priority(ai_feedback)
        print(f"[INFO] AI Review Priority Score: {analysis['priority_score']}/100")
        if analysis["high_risk"]:
            print("[ALERT] High-risk issues detected in PR feedback.")

        with open("ai_review.md", "w", encoding="utf-8") as f:
            f.write(ai_feedback)
        print("[INFO] Saved AI feedback to ai_review.md")

        # Post to PR
        print("[INFO] Posting AI feedback as a GitHub PR comment...")
        comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        response = requests.post(
            comment_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            json={"body": f"### AI PR Review\n\n{ai_feedback}"}
        )

        if response.status_code == 201:
            print("[SUCCESS] Successfully posted comment to PR!")
            save_metadata(mode, success=True)
        else:
            print(f"[ERROR] Failed to post comment: {response.status_code} - {response.text}")
            save_metadata(mode, success=False)

    except Exception as e:
        print(f"[FATAL] OpenAI request failed: {e}")
        save_metadata(mode, success=False)

    print(f"\n[SUMMARY] Review complete — Mode: {mode}")
    print("[SUMMARY] Feedback saved to ai_review.md")
    print("[SUMMARY] Metadata saved to review_metadata.json")

from .review_memory import update_history   

content_preview = diff_content[:1000]  # small slice to hash & detect duplicates
metrics = update_history(
    pr_number=str(pr_number),
    title=title,
    category=category,
    priority_score=analysis.get("priority_score", 0),
    high_risk=analysis.get("high_risk", False),
    content_preview=content_preview,
    extra={"ai_mode": mode}
)
print(f"[INFO] History metrics after update: avg_score={metrics.get('avg_priority_score')}, total={metrics.get('total_reviews')}")



if __name__ == "__main__":
    main()


















