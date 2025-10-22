"""
Static security + quality check script.
Runs Ruff, Bandit, and Mypy to generate a combined static_report.json.
"""

import json, subprocess, sys, os, tempfile

def run_cmd(cmd):
    print(f"[RUN] {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[WARN] Command exited {res.returncode}")
    return res.stdout

def main():
    report = {}

    # Ruff (style + lint)
    try:
        out = run_cmd("ruff check . --format json")
        report["ruff"] = json.loads(out) if out.strip() else []
    except Exception as e:
        report["ruff"] = {"error": str(e)}

    # Bandit (security)
    try:
        out = run_cmd("bandit -r . -f json")
        report["bandit"] = json.loads(out) if out.strip() else {}
    except Exception as e:
        report["bandit"] = {"error": str(e)}

    # Mypy (types)
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    tmpfile.close()
    try:
        out = run_cmd(f"mypy . --ignore-missing-imports --show-error-codes --pretty --json-report {tmpfile.name}")
        # If mypy JSON output exists, load it
        if os.path.exists(f"{tmpfile.name}.json"):
            with open(f"{tmpfile.name}.json") as f:
                report["mypy"] = json.load(f)
        else:
            report["mypy"] = {"raw_output": out}
    except Exception as e:
        report["mypy"] = {"error": str(e)}

    # Save
    with open("static_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("[SUCCESS] Wrote static_report.json")

if __name__ == "__main__":
    main()
