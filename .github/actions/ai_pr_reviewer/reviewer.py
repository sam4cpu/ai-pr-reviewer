import os
import requests
import json

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GITHUB_TOKEN")

    print(f" Fetching data for PR #{pr_number} in {repo}...")

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f" Failed to fetch PR data: {response.status_code}")
        print(response.text)
        return

    pr_data = response.json()

    print(" PR Data successfully retrieved:")
    print(f"Title: {pr_data['title']}")
    print(f"Author: {pr_data['user']['login']}")
    print(f"Branch: {pr_data['head']['ref']}")
    print(f"Base: {pr_data['base']['ref']}")
    print(f"URL: {pr_data['html_url']}")

    # Save to JSON for artifact upload
    with open("pr_data.json", "w") as f:
        json.dump(pr_data, f, indent=2)

    print(" PR data saved to pr_data.json")

if __name__ == "__main__":
    main()









