import os
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import mean

REVIEW_PATH = Path("artifacts/ai_review.md")
CONF_FILE = Path("reviewer_confidence.json")
WEIGHTS_FILE = Path("adaptive_weights.json")
OUTPUT_JSON = Path("review_summary.json")
OUTPUT_MD = Path("review_summary.md")

def load_json_safely(path: Path, default=None):
    """Safely load JSON data, returning a default if unavailable."""
    if not path.exists():
        print(f"[WARN] {path} not found, using default baseline.")
        return default or {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Could not parse {path.name}: {e}")
        return default or {}

def extract_section(text, header):
    """Extracts a markdown section by its header."""
    pattern = rf"##+ {header}[\s\S]*?(?=\n##|\Z)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0).strip() if match else f"_{header} section missing_"

def count_bullets(section_text):
    """Counts bullet points for simple metrics."""
    return len(re.findall(r"^- ", section_text, flags=re.MULTILINE))

def detect_high_risk_terms(text):
    """Scans for risk-related words (security, crashes, etc.)."""
    risk_terms = [
        "security", "vulnerability", "crash", "data loss",
        "leak", "injection", "auth", "password", "corruption"
    ]
    lowered = text.lower()
    return [term for term in risk_terms if term in lowered]

def compute_confidence_score(summary, issues, suggestions, risks, calibrated_conf):
    """Computes a calibrated AI confidence score."""
    length_factor = len(summary) / 200
    balance = abs(count_bullets(issues) - count_bullets(suggestions))

    base_score = calibrated_conf * 100
    base_score -= balance * 5
    base_score -= 10 if "missing" in summary.lower() else 0
    base_score -= len(risks) * 5
    if length_factor < 0.5:
        base_score -= 5

    return max(30, min(98, round(base_score)))

def generate_summary():
    print("[START] Generating recruiter-oriented summary...")

    if not REVIEW_PATH.exists():
        print("[FATAL] No ai_review.md found — make sure reviewer artifacts are generated first.")
        return

    # Load optional data
    confidence = load_json_safely(CONF_FILE, {"calibrated_confidence": 0.5})
    weights = load_json_safely(WEIGHTS_FILE, {})
    numeric_weights = [v for v in weights.values() if isinstance(v, (int, float))]
    insight_depth = mean(numeric_weights) * 10 if numeric_weights else 50
    if not numeric_weights:
        print("[WARN] No numeric weights found; using neutral baseline for insight depth.")

    # Read review markdown
    review_text = REVIEW_PATH.read_text(encoding="utf-8")
    summary = extract_section(review_text, "Summary")
    issues = extract_section(review_text, "Potential Issues")
    suggestions = extract_section(review_text, "Suggestions")
    tests = extract_section(review_text, "Testing Recommendations")

    # Compute analytics
    risks = detect_high_risk_terms(review_text)
    score = compute_confidence_score(
        summary, issues, suggestions, risks, confidence.get("calibrated_confidence", 0.5)
    )

    # Compose summary
    summary_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "avg_confidence": confidence.get("calibrated_confidence", 0.5) * 100,
        "insight_depth": insight_depth,
        "confidence_score": score,
        "potential_issues": count_bullets(issues),
        "suggestions": count_bullets(suggestions),
        "high_risk_terms": risks,
    }

    # Write JSON
    OUTPUT_JSON.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    print(f"[INFO] Saved structured summary → {OUTPUT_JSON}")

    # Write Markdown (recruiter format)
    md_content = f"""##  AI Review Summary 

**Confidence Score:** {score}/100  
**Calibrated Confidence:** {summary_data['avg_confidence']:.1f}%  
**Insight Depth:** {insight_depth:.1f}  
**Detected Issues:** {summary_data['potential_issues']}  
**Suggestions:** {summary_data['suggestions']}  
**High-Risk Keywords:** {', '.join(risks) if risks else 'None'}

###  Summary
{summary}

### ⚠️ Potential Issues
{issues}

###  Suggestions
{suggestions}

###  Testing Recommendations
{tests}

---

_This summary was generated autonomously by the AI Reviewer Network (v20.5)._
"""
    OUTPUT_MD.write_text(md_content, encoding="utf-8")
    print(f"[SUCCESS] {OUTPUT_MD.name} generated successfully.")

if __name__ == "__main__":
    generate_summary()


