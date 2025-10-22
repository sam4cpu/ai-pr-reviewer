"""
Benchmark harness for the AI PR Reviewer.
Measures execution time, token-size proxy, and scoring stability
across a fixed set of synthetic diffs.
"""

import os, json, time, random, statistics, hashlib

BENCH_DIR = "benchmarks/data"
os.makedirs(BENCH_DIR, exist_ok=True)

def synthetic_diffs(n=3):
    for i in range(n):
        yield f"diff --git a/test{i}.py b/test{i}.py\n+print('bench{i}')\n"

def mock_review(diff: str) -> dict:
    # simulate AI latency and pseudo "score"
    time.sleep(0.1)
    token_proxy = len(diff) / 5
    clarity = 80 + random.randint(-5, 5)
    actionability = 75 + random.randint(-5, 5)
    score = (clarity + actionability) / 2
    return {"clarity": clarity, "actionability": actionability,
            "score": score, "tokens": token_proxy}

def main():
    results = []
    start_total = time.time()
    for i, diff in enumerate(synthetic_diffs()):
        start = time.time()
        r = mock_review(diff)
        elapsed = time.time() - start
        r["latency"] = elapsed
        results.append(r)
    total_time = time.time() - start_total

    summary = {
        "runs": len(results),
        "avg_score": round(statistics.mean(r["score"] for r in results), 2),
        "avg_latency_s": round(statistics.mean(r["latency"] for r in results), 3),
        "avg_tokens": round(statistics.mean(r["tokens"] for r in results), 1),
        "checksum": hashlib.sha1(json.dumps(results).encode()).hexdigest()[:10],
        "total_time": round(total_time, 3)
    }

    os.makedirs("benchmarks", exist_ok=True)
    with open("benchmarks/benchmark_report.json", "w") as f:
        json.dump({"results": results, "summary": summary}, f, indent=2)

    print(f"[BENCHMARK] Completed {summary['runs']} runs in {summary['total_time']} s")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
