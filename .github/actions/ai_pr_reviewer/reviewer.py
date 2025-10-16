import os
import json
import requests
from openai import OpenAI

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")

    print(f" Starting AI PR Review for {repo} (PR #{pr_number})...")

    # Fetch PR data again
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f" GitHub API error: {response.status_code}")
        return

    pr_data = response.json()
    title = pr_data.get("title", "")
    body = pr_data.get("body", "")

    print(f" Fetched PR: {title}")

    # Initialize OpenAI client
    client = OpenAI(api_key=openai_key)

    prompt = f"""
    You are a senior software engineer reviewing a pull request.
    Here is the PR title and description:

    Title: {title}
    Description: {body}

    Provide a brief, professional summary of what this PR likely does,
    any potential improvements or risks, and next steps for testing.
    """

    print(" Sending request to OpenAI...")

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional code reviewer."},
                {"role": "user", "content": prompt}
            ]
        )

        ai_feedback = completion.choices[0].message.content
        print("\n AI Review Feedback:\n")
        print(ai_feedback)

        with open("ai_review.txt", "w") as f:
            f.write(ai_feedback)

        print("\n Saved AI feedback to ai_review.txt")

    except Exception as e:
        print(f" Error during OpenAI request: {e}")

if __name__ == "__main__":
    main()










