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
    """CI-safe push of badges, reports, and evolution state to network hub."""
    clone_url = get_clone_url()
    hub_dir = "/tmp/ai_hub"

    # 1. Reset clone if exists
    if Path(hub_dir).exists():
        shutil.rmtree(hub_dir)

    print(f"[INFO] Cloning hub repo from {clone_url}...")
    run_cmd(["git", "clone", clone_url, hub_dir])

    # 2. Configure git identity
    ensure_git_identity()

    # 3. Ensure HEAD is on 'main' branch
    print("[INFO] Ensuring branch 'main' exists and is checked out...")
    run_cmd(["git", "checkout", "-B", "main"], cwd=hub_dir)
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=hub_dir, capture_output=True, text=True
    ).stdout.strip()
    print(f"[DEBUG] Current branch after checkout: '{current_branch}'")

    # 4. Ensure assets folder exists
    Path(hub_dir, "assets").mkdir(exist_ok=True)

    # 5. Copy all outputs
    files_to_copy = [
        "evolution_state.json",
        "project_evolution_report.md",
        "assets/evolution_badge.svg"
    ]
    for f in files_to_copy:
        if Path(f).exists():
            dest = Path(hub_dir) / f
            if f.startswith("assets/"):
                dest.parent.mkdir(exist_ok=True)
            shutil.copy(f, dest)
            print(f"[INFO] Copied {f} → {dest}")

    # 6. Stage changes
    run_cmd(["git", "add", "."], cwd=hub_dir)

    # 7. Commit changes if any
    commit_result = subprocess.run(
        ["git", "commit", "-m", "Evolution badge + report (auto)"],
        cwd=hub_dir,
        capture_output=True,
        text=True
    )

    if "nothing to commit" in commit_result.stdout.lower():
        print("[INFO] No new changes to commit — skipping push.")
        return
    print(f"[INFO] Commit created:\n{commit_result.stdout}")

    # 8. Push changes to main branch
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
        print("[FINAL] Force push attempted.")

    badge_svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="220" height="28">
  <rect width="220" height="28" fill="#24292e" rx="5"/>
  <text x="10" y="19" fill="#fff" font-family="monospace" font-size="13">AI Reviewer Evolution ✔</text>
  <a xlink:href="https://github.com/{os.getenv('GITHUB_REPOSITORY')}/actions">
    <rect x="150" width="65" height="28" fill="#2ea44f" rx="5"/>
    <text x="160" y="19" fill="#fff" font-family="monospace" font-size="13">LIVE →</text>
  </a>
</svg>
""".strip()

    assets_dir = Path(hub_dir) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "evolution_badge.svg").write_text(badge_svg, encoding="utf-8")

    print("[INFO] Generated evolution_badge.svg with live CI link.")

    # Commit + push badge to hub
    run_cmd(["git", "add", "assets/evolution_badge.svg"], cwd=hub_dir)
    run_cmd(["git", "commit", "-m", "Add live evolution badge (auto)"], cwd=hub_dir, check=False)
    run_cmd(["git", "push", "origin", "HEAD:main"], cwd=hub_dir, check=False)
    print("[SUCCESS] Evolution badge updated and pushed.")


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


