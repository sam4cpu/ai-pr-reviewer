import os
import subprocess
from pathlib import Path
from datetime import datetime

HUB_REPO = os.getenv("NETWORK_HUB_REPO", "").strip()
WORK_DIR = "/home/runner/work/ai-pr-reviewer/ai-pr-reviewer"
HUB_DIR = "/tmp/ai_hub"

def safe_run(cmd, check=True, capture=False):
    """Run shell command safely and log clearly."""
    print(f"[CMD] {' '.join(cmd)}")
    try:
        if capture:
            return subprocess.run(cmd, check=check, text=True, capture_output=True)
        else:
            subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        raise

def push():
    """Push generated summary and badge to global hub repo."""
    if not HUB_REPO:
        raise RuntimeError("NETWORK_HUB_REPO secret not set in GitHub Secrets!")

    clone_url = f"https://{HUB_REPO}" if not HUB_REPO.startswith("https") else HUB_REPO
    print(f"[INFO] Cloning hub repo from {clone_url}...")

    # Clean old clone if exists
    if os.path.exists(HUB_DIR):
        subprocess.run(["rm", "-rf", HUB_DIR], check=True)

    # --- Clone hub repo ---
    safe_run(["git", "clone", clone_url, HUB_DIR])

    os.chdir(HUB_DIR)
    safe_run(["git", "checkout", "main"])
    safe_run(["git", "pull", "origin", "main"])

    # --- Configure bot identity ---
    safe_run(["git", "config", "user.name", "AI Reviewer Bot"])
    safe_run(["git", "config", "user.email", "bot@ai-reviewer.local"])

    # --- Copy new artifacts from the project workspace ---
    artifacts = [
        "assets/evolution_badge.svg",
        "evolution_state.json",
        "project_evolution_report.md",
        "recruiter_summary.md",
        "review_summary.md",
    ]
    for artifact in artifacts:
        src = Path(WORK_DIR) / artifact
        if src.exists():
            safe_run(["cp", str(src), "."])
        else:
            print(f"[WARN] Missing artifact: {artifact}")

    # --- Check for changes ---
    result = safe_run(["git", "status", "--porcelain"], capture=True)
    if not result.stdout.strip():
        print("[INFO] No changes to commit. Skipping push.")
        return

    commit_msg = f"Evolution badge + report (auto) — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    safe_run(["git", "add", "."])
    safe_run(["git", "commit", "-m", commit_msg])
    safe_run(["git", "push", "origin", "main"])

    print("[SUCCESS] Summary & badge synced successfully to network hub.")

if __name__ == "__main__":
    print("[START] Pushing summary & badge to network hub...")
    try:
        push()
    except Exception as e:
        print(f"[FATAL] Global sync failed: {e}")
        exit(1)

