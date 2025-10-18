import os
import time
import requests
from openai import OpenAI, APIError, RateLimitError


def request_with_retry(client, messages, model="gpt-4o-mini", max_retries=3):
    """Send a chat completion request with retry logic for rate limits and transient errors."""
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
            print(f"[WARN] Rate limit reached. Retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
            time.sleep(wait_time)

        except APIError as e:
            print(f"[ERROR] API error: {e}. Retrying (attempt {attempt}/{max_retries})...")
            time.sleep(3)

        except Exception as e:
            print(f"[ERROR] Unexpected exception: {e}")
            break

    print("[FAIL] Exceeded maximum retry attempts.")
    return None


def read_diff_file(path="pr_diff.patch"):
    """Read the diff file generated from the PR."""
    if not os.path.exists(path):
        print("[WARN] No diff file found.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        diff = f.read()
    print(f"[INFO] Loaded diff file ({len(diff)} characters)")
    return diff[:8000]  # limit for token safety


def main():
    # --- Environment setup ---
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token, openai_key]):
        print("[ERROR] Missing one or more required environment variables.")
        return

    print(f"[INFO] Starting AI PR Review for {repo} (PR #{pr_number})")

    # --- Fetch PR metadata ---
    headers = {"Authorization": f"Bearer {token}"}
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_data = requests.get(pr_url, headers=headers).json()
    title = pr_data.get("title", "(No title)")
    body = pr_data.get("body", "(No description)")

    print(f"[INFO] Fetched PR metadata: {title}")

    # --- Load diff ---
    diff_content = read_diff_file()
    if not diff_content:
        print("[ERROR] No diff available for analysis. Exiting.")
        return

    # --- Initialize OpenAI client ---
    client = OpenAI(api_key=openai_key)

    # --- Build prompt ---
    prompt = f"""
    You are a senior software engineer reviewing a pull request.

    **PR Title:** {title}
    **Description:** {body}

    Below is the unified diff of the code changes:
    {diff_content}

    Please analyze this diff and provide structured review feedback in markdown format:

    ## AI Code Review Feedback

    ### Summary
    - Summarize what this PR changes.

    ### Potential Issues
    - List possible bugs, logic errors, or risky design choices.

    ### Suggestions
    - Suggest code improvements or refactors.

    ### Testing Recommendations
    - Recommend relevant pytest tests or scenarios.
    """

    print("[INFO] Sending diff to OpenAI for analysis...")

    # --- Send to OpenAI with retry logic ---
    ai_feedback = request_with_retry(
        client,
        [
            {"role": "system", "content": "You are a professional software engineer."},
            {"role": "user", "content": prompt},
        ],
    )

    if not ai_feedback:
        print("[ERROR] No feedback returned after retries. Aborting.")
        return

    print("\n[RESULT] AI Review Feedback:\n")
    print(ai_feedback)

    # --- Save feedback locally ---
    with open("ai_review.md", "w", encoding="utf-8") as f:
        f.write(ai_feedback)

    print("[INFO] Saved AI feedback to ai_review.md")

    # --- Post feedback as PR comment ---
    print("[INFO] Posting AI feedback as a GitHub PR comment...")

    comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    comment_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    comment_body = {"body": f"### AI PR Review\n\n{ai_feedback}"}

    response = requests.post(comment_url, headers=comment_headers, json=comment_body)

    if response.status_code == 201:
        print("[SUCCESS] Successfully posted comment to PR.")
    else:
        print(f"[ERROR] Failed to post comment: {response.status_code} - {response.text}")


if __name__ == "__main__":
    main()














