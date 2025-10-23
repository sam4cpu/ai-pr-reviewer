import os
import shutil
import subprocess
from pathlib import Path

HUB_DIR = Path("/tmp/ai_hub")
LOCAL_ADAPTIVE = Path("adaptive_weights.json")
NETWORK_ADAPTIVE_LOCAL = Path("adaptive_network_weights.json")

def run(cmd, cwd=None):
    print(f"> {cmd}")
    subprocess.check_call(cmd, shell=True, cwd=cwd)

def pull():
    repo = os.getenv("NETWORK_HUB_REPO")
    token = os.getenv("NETWORK_HUB_TOKEN")
    if not repo or not token:
        print("[WARN] NETWORK_HUB_REPO or NETWORK_HUB_TOKEN not set. Skipping pull.")
        return
    if HUB_DIR.exists():
        shutil.rmtree(HUB_DIR)
    clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    try:
        run(f"git clone --depth=1 {clone_url} {HUB_DIR}")
        candidate = HUB_DIR / "adaptive_network_weights.json"
        if candidate.exists():
            shutil.copy(candidate, NETWORK_ADAPTIVE_LOCAL)
            print(f"[INFO] Copied {candidate} -> {NETWORK_ADAPTIVE_LOCAL}")
        else:
            print("[INFO] Hub has no adaptive_network_weights.json")
    except Exception as e:
        print(f"[WARN] Failed to pull hub repo: {e}")

def push():
    repo = os.getenv("NETWORK_HUB_REPO")
    token = os.getenv("NETWORK_HUB_TOKEN")
    if not repo or not token:
        print("[WARN] NETWORK_HUB_REPO or NETWORK_HUB_TOKEN not set. Skipping push.")
        return
    if not Path("adaptive_network_weights.json").exists():
        print("[WARN] No adaptive_network_weights.json to push. Skipping.")
        return
    tmp = HUB_DIR
    if tmp.exists():
        shutil.rmtree(tmp)
    clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    try:
        run(f"git clone {clone_url} {tmp}")
        dest = tmp / f"adaptive_network_weights_{os.getenv('GITHUB_RUN_ID','local')}.json"
        shutil.copy("adaptive_network_weights.json", dest)
        run("git add .", cwd=tmp)
        run(f'git commit -m "Add adaptive network snapshot from {os.getenv("GITHUB_REPOSITORY","local")}"', cwd=tmp)
        run("git push origin HEAD", cwd=tmp)
        print("[INFO] Pushed adaptive snapshot to hub (may create a new commit).")
    except Exception as e:
        print(f"[WARN] Failed to push to hub: {e}")

if __name__ == "__main__":
    import sys
    cmd = (sys.argv[1] if len(sys.argv)>1 else "pull").lower()
    if cmd == "pull":
        pull()
    else:
        push()
