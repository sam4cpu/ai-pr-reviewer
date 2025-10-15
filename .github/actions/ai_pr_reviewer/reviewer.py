import os
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    logging.info(" AI PR Reviewer started")

    # GitHub provides this automatically for Actions
    event_path = os.getenv("GITHUB_EVENT_PATH")
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")  # e.g., "sam4cpu/ai-pr-reviewer"

    if not all([event_path, github_token, repo]):
        logging.error("Missing environment variables. Exiting.")
        return

    # Read PR info from the event payload
    with open(event_path, "r") as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    pr_number = pr.get("number")
    if not pr_number:
        logging.error("No pull request number found.")
        return

    logging.info(f" Fetching changed files for PR #{pr_number} in {repo}")

    # Build the GitHub API request
    api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {"Authorization": f"Bearer {github_token}"}

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        logging.error(f"GitHub API error: {response.status_code} {response.text}")
        return

    files = response.json()
    logging.info(f"🧩 Found {len(files)} changed files")

    for fdata in files:
        filename = fdata["filename"]
        status = fdata["status"]
        additions = fdata["additions"]
        deletions = fdata["deletions"]
        logging.info(f" {filename} (+{additions}/-{deletions}) [{status}]")

    logging.info(" Data fetch complete — ready for AI analysis next stage.")

if __name__ == "__main__":
    main()








