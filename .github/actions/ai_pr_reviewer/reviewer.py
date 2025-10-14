import os, json, logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    logging.info("✅ AI PR Reviewer triggered successfully!")

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        logging.warning("No GitHub event file found — running in test mode.")
        return

    with open(event_path, "r") as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    title = pr.get("title", "Unknown")
    user = pr.get("user", {}).get("login", "Unknown")
    branch = pr.get("head", {}).get("ref", "Unknown")

    logging.info(f"🔹 PR Title: {title}")
    logging.info(f"👤 Author: {user}")
    logging.info(f"🌿 Branch: {branch}")

if __name__ == "__main__":
    main()






