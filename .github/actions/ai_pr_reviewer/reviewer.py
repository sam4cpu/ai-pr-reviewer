import os
import json

def main():
    print("✅ AI PR Reviewer triggered successfully!")

    event_path = os.getenv("GITHUB_EVENT_PATH")

    if not event_path or not os.path.exists(event_path):
        print("⚠️ No GitHub event file found — running in test mode.")
        return

    # Load PR data from the event file GitHub provides
    with open(event_path, "r") as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    title = pr.get("title", "Unknown")
    user = pr.get("user", {}).get("login", "Unknown")
    branch = pr.get("head", {}).get("ref", "Unknown")

    print(f"🔹 PR Title: {title}")
    print(f"👤 Author: {user}")
    print(f"🌿 Branch: {branch}")

if __name__ == "__main__":
    main()





