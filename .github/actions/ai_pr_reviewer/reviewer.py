import os
import requests
import time
from openai import OpenAI, APIError, RateLimitError

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
    return diff[:8000]  # Token safety

def gather_repo_context(base_path="."):
    """Collect key contextual files (README, tests, dependencies)."""
    important_files = [
        "README.md",
        "requirements.txt",
        "pyproject.toml"
    ]

    context_snippets = []

    for file in important_files:
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()[:2000]  # Limit per file
            context_snippets.append(f"### {file}\n{content}")

    # Optionally gather test files for context
    test_dir = os.path.join(base_path, "tests")
    if os.path.isdir(test_dir):
        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.endswith(".py"):
                    test_path = os.path.join(root, file)
                    with open(test_path, "r", encoding="utf-8") as f:
                        content = f.read()[:1000]
                    context_snippets.append(f"### {test_path}\n{content}")

    if not context_snippets:
        print("[INFO] No contextual files found.")
    else:
        print(f"[INFO] Loaded context from {len(context_snippets)} files.")

    return "\n\n".join(context_snippets)

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token, openai_key]):
        print("[FATAL] Missing one or more required environment variables.")
        return

    print(f"[START] Running AI PR Review for {repo} (PR #{pr_number})...")

    # Fetch PR metadata 
    headers = {"Authorization": f"Bearer {token}"}
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_data = requests.get(pr_url, headers=headers).json()
    title = pr_data.get("title", "")
    body = pr_data.get("body", "")

    print(f"[INFO] Fetched PR: {title}")

    # Load diff file 
    diff_content = read_diff_file()
    if not diff_content:
        print("[WARN] No diff to analyze, exiting.")
        return

    # Load repo context 
    repo_context = gather_repo_context()
    print("[INFO] Loaded repository context for review.")

    # Initialize OpenAI 
    client = OpenAI(api_key=openai_key)

    # Build prompt
    prompt = f"""
You are a senior software engineer reviewing a pull request.

**PR Title:** {title}
**Description:** {body}

### Repository Context
{repo_context}

### Code Diff
{diff_content}

Provide structured, concise markdown feedback that considers both
the code diff and overall project context.

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

    try:
        ai_feedback = request_with_retry(client, [
            {"role": "system", "content": "You are a professional software engineer reviewing code."},
            {"role": "user", "content": prompt}
        ])

        if not ai_feedback:
            print("[FAIL] No feedback returned after retries.")
            return

        print("\n[OUTPUT] AI Review Feedback:\n")
        print(ai_feedback)

        # Save review feedback locally
        with open("ai_review.md", "w", encoding="utf-8") as f:
            f.write(ai_feedback)
        print("[INFO] Saved AI feedback to ai_review.md")

        # --- Post feedback to PR ---
        print("[INFO] Posting AI feedback as a GitHub PR comment...")
        comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        comment_headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        comment_body = {"body": f"### 🤖 AI PR Review\n\n{ai_feedback}"}
        response = requests.post(comment_url, headers=comment_headers, json=comment_body)

        if response.status_code == 201:
            print("[SUCCESS] Successfully posted comment to PR!")
        else:
            print(f"[ERROR] Failed to post comment: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[FATAL] OpenAI request failed: {e}")

if __name__ == "__main__":
    main()















