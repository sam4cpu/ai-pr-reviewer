import os
import subprocess
import json
import shutil
from pathlib import Path

def run_cmd(cmd, cwd=None, check=True):
    """Run a shell command safely with debug output."""
    print(f"[CMD] {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        if check:
            raise
        else:
            return False
    return True

def get_clone_url():
    """Safely construct clone URL using repo + token secrets."""
    token = os.getenv("NETWORK_HUB_TOKEN", "").strip()
    repo_url = os.getenv("NETWORK_HUB_REPO", "").strip()

    if not repo_url:
        raise RuntimeError("[FATAL] Missing NETWORK_HUB_REPO secret.")

    if not repo_url.startswith("https://github.com/"):
        print(f"[WARN] NETWORK_HUB_REPO should be a full GitHub HTTPS URL, not '{repo_url}'.")

    # Inject token only if provided
    if token:
        if repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://x-access-token:{token}@")
        else:
            return f"https://x-access-token:{token}@{repo_url}"
    else:
        print("[WARN] No NETWORK_HUB_TOKEN found — cloning unauthenticated (public hub only).")
        return repo_url

def ensure_git_identity():
    """Ensure git identity is configured inside CI."""
    run_cmd(["git", "config", "--global", "user.email", "ai-reviewer-bot@github.com"], check=False)
    run_cmd(["git", "config", "--global", "user.name", "AI Reviewer Bot"], check=False)

def pull():
    """Pull latest global hub state."""
    clone_url = get_clone_url()
    hub_dir = "/tmp/ai_hub"

    if Path(hub_dir).exists():
        shutil.rmtree(hub_dir)
    print(f"[INFO] Cloning hub repo from {clone_url}...")
    run_cmd(["git", "clone", clone_url, hub_dir])

    target = Path("global_state.json")
    src = Path(hub_dir) / "global_state.json"
    if src.exists():
        shutil.copy(src, target)
        print(f"[SUCCESS] Pulled global state → {target}")
    else:
        print("[WARN] No global_state.json found in hub repo (new network?)")

def push():
    """Push new badges, metrics, or summaries to global hub in a CI-safe way."""
    clone_url = get_clone_url()
    hub_dir = "/tmp/ai_hub"

    # 1. Reset clone if it exists
    if Path(hub_dir).exists():
        shutil.rmtree(hub_dir)

    print(f"[INFO] Cloning hub repo from {clone_url}...")
    run_cmd(["git", "clone", clone_url, hub_dir])

    # 2. Ensure git identity
    ensure_git_identity()

    # 3. Checkout or create 'main' branch BEFORE making any changes
    print("[INFO] Switching to branch 'main' before any commits...")
    run_cmd(["git", "checkout", "-B", "main"], cwd=hub_dir)

    # Verify current branch (debug)
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=hub_dir,
        capture_output=True,
        text=True
    )
    print(f"[DEBUG] Current branch after checkout: '{branch_result.stdout.strip()}'")

    # 4. Ensure assets directory exists
    Path(hub_dir, "assets").mkdir(exist_ok=True)

    # 5. Copy files to hub directory
    for f in ["evolution_state.json", "project_evolution_report.md"]:
        if Path(f).exists():
            shutil.copy(f, Path(hub_dir, f))
            print(f"[INFO] Copied {f} → hub")

    if Path("assets/evolution_badge.svg").exists():
        shutil.copy("assets/evolution_badge.svg", Path(hub_dir, "assets/evolution_badge.svg"))

    # 6. Stage changes
    run_cmd(["git", "add", "."], cwd=hub_dir)

    # 7. Commit changes
    commit_result = subprocess.run(
        ["git", "commit", "-m", "Evolution badge + report (auto)"],
        cwd=hub_dir,
        capture_output=True,
        text=True
    )

    if "nothing to commit" in commit_result.stdout.lower():
        print("[INFO] No changes to commit — skipping push.")
        return
    print(f"[INFO] Commit created:\n{commit_result.stdout}")

    # 8. Push to main branch
    print("[INFO] Pushing changes to 'main'...")
    push_result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=hub_dir,
        capture_output=True,
        text=True
    )

    if push_result.returncode == 0:
        print("[SUCCESS] Synced global report + badge to hub.")
    else:
        print("[WARN] Push failed — attempting force push...")
        run_cmd(["git", "push", "origin", "main", "--force"], cwd=hub_dir, check=False)
        print("[FINAL] Force push attempted (safe for CI).")


if __name__ == "__main__":
    mode = os.getenv("MODE", "").strip().lower()
    import sys
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    if mode == "pull":
        pull()
    elif mode == "push":
        push()
    else:
        print("Usage: python global_sync.py [pull|push]")


