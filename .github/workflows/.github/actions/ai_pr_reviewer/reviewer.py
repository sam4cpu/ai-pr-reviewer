import os
import json

def load_event():
    """Load the GitHub event payload (details about the PR)."""
    with open(os.getenv('GITHUB_EVENT_PATH')) as f:
        return json.load(f)

def main():
    event = load_event()
    pr_number = event["number"]
    repo_name = event["repository"]["full_name"]

    print(f"✅ AI PR Reviewer triggered on PR #{pr_number} in {repo_name}")
    print("👋 Hello from your GitHub Action!")

if __name__ == "__main__":
    main()


