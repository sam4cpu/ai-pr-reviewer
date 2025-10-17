import os
import requests
from openai import OpenAI

def read_diff_file(path="pr_diff.patch"):
    if not os.path.exists(path):
        print(" No diff file found.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        diff = f.read()
    print(f" Loaded diff file ({len(diff)} chars)")
    return diff[:8000]  # limit for token safety

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([repo, pr_number, token, openai_key]):
        print(" Missing one or more required environment variables.")
        return


    print(f" Starting AI PR Review for {repo} (PR #{pr_number})...")

    # Fetch PR info (title + description)
    headers = {"Authorization": f"Bearer {token}"}
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_data = requests.get(pr_url, headers=headers).json()
    title = pr_data.get("title", "")
    body = pr_data.get("body", "")

    print(f" Fetched PR: {title}")

    # Load diff
    diff_content = read_diff_file()
    if not diff_content:
        print(" No diff to analyze, exiting.")
        return

    # Initialize OpenAI
    client = OpenAI(api_key=openai_key)

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

    print(" Sending diff to OpenAI for analysis...")

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional software engineer."},
                {"role": "user", "content": prompt}
            ]
        )

        ai_feedback = completion.choices[0].message.content
        print("\n AI Review Feedback:\n")
        print(ai_feedback)

        with open("ai_review.md", "w", encoding="utf-8") as f:
            f.write(ai_feedback)

        print("\n Saved AI feedback to ai_review.md")
        # --- Post the AI feedback as a PR comment ---
        print("\n Posting AI feedback as a GitHub PR comment...")

        comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        comment_headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        comment_body = {"body": f"### 🤖 AI PR Review\n\n{ai_feedback}"}

        response = requests.post(comment_url, headers=comment_headers, json=comment_body)

        if response.status_code == 201:
            print(" Successfully posted comment to PR!")
        else:
            print(f" Failed to post comment: {response.status_code} - {response.text}")

    except Exception as e:
        print(f" Error during OpenAI request: {e}")

if __name__ == "__main__":
    main()











