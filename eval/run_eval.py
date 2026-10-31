"""Detector evaluation: regex baseline vs learned classifier vs both.

No LLM calls. Writes results/detector_eval.json and results/detector_eval.md.
Run after data/build_dataset.py and python -m guard.classifier.
"""
from __future__ import annotations

import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from guard import rules  # noqa: E402
from guard.classifier import Detector  # noqa: E402
from guard.core import Guard  # noqa: E402

DATA, OUT = ROOT / "data", ROOT / "results"


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open() if l.strip()] if p.exists() else []


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def main():
    clf = Detector()
    detectors = {d: Guard(detector=d, clf=clf) for d in ("regex", "classifier", "either")}
    report = {"python": platform.python_version(), "threshold": clf.threshold, "comment_level": {}, "snippet_level": {},
              "latency_ms": {}}

    groups = {
        "attack/synthetic_test (held-out templates)": [r for r in load(DATA / "test.jsonl") if r["label"] == 1],
        "attack/commentinject_released (external)": load(DATA / "external.jsonl"),
        "clean/cpython_stdlib_test (held-out files)": [r for r in load(DATA / "test.jsonl") if r["source"] == "cpython_stdlib"],
        "clean/cpython_headers_test (held-out files)": [r for r in load(DATA / "test.jsonl") if r["source"] == "cpython_headers"],
        "clean/hard_negative_test": [r for r in load(DATA / "test.jsonl") if r["family"] == "hard_negative"],
    }
    for name, rows in groups.items():
        texts = [r["text"] for r in rows]
        report["comment_level"][name] = {}
        for d, g in detectors.items():
            hits = sum(s[2] for s in g.score_texts(texts))
            report["comment_level"][name][d] = rate(hits, len(rows))

    snippet_sets = {}
    for r in load(DATA / "snippets_test.jsonl") + load(DATA / "snippets_adaptive.jsonl") + \
            load(DATA / "derived" / "primevul_clean.jsonl"):
        snippet_sets.setdefault(r["set"], []).append(r)
    for name, rows in snippet_sets.items():
        report["snippet_level"][name] = {}
        for d, g in detectors.items():
            hits = sum(g.scan(r["code"], r["language"]).flagged for r in rows)
            report["snippet_level"][name][d] = rate(hits, len(rows))
    # Per adaptive strategy, for the README's honest-failure table.
    adaptive = snippet_sets.get("adaptive", [])
    report["adaptive_by_strategy"] = {}
    for strat in sorted({r["strategy"] for r in adaptive}):
        rows = [r for r in adaptive if r["strategy"] == strat]
        report["adaptive_by_strategy"][strat] = {d: rate(sum(g.scan(r["code"], "python").flagged for r in rows), len(rows))
                                                for d, g in detectors.items()}

    # Latency of the guard alone (extract + score + strip), single process, warm.
    bench = [r for rows in snippet_sets.values() for r in rows]
    g = detectors["either"]
    for r in bench[:50]:
        g.scan(r["code"], r["language"])
    times = []
    for r in bench:
        t0 = time.perf_counter()
        g.scan(r["code"], r["language"])
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    report["latency_ms"] = {"n": len(times), "p50": round(statistics.median(times), 3),
                            "p95": round(times[int(0.95 * (len(times) - 1))], 3),
                            "machine": f"{platform.machine()} {platform.system()}"}

    OUT.mkdir(exist_ok=True)
    (OUT / "detector_eval.json").write_text(json.dumps(report, indent=2))
    lines = [f"Threshold {clf.threshold:.3f}. Python {report['python']}. Rates with Wilson 95% CI.", "",
             "| Set | n | Regex | Classifier | Either |", "|---|---|---|---|---|"]

    def cell(x):
        return f"{100 * x['rate']:.1f}% ({100 * x['ci95'][0]:.1f} to {100 * x['ci95'][1]:.1f})" if x["n"] else "n/a"
    for level in ("comment_level", "snippet_level"):
        for name, v in report[level].items():
            lines.append(f"| {level.split('_')[0]}: {name} | {v['regex']['n']} | {cell(v['regex'])} | "
                         f"{cell(v['classifier'])} | {cell(v['either'])} |")
    lines += ["", "| Adaptive strategy | Regex | Classifier | Either |", "|---|---|---|---|"]
    for s, v in report["adaptive_by_strategy"].items():
        lines.append(f"| {s} | {100 * v['regex']['rate']:.0f}% | {100 * v['classifier']['rate']:.0f}% | {100 * v['either']['rate']:.0f}% |")
    lt = report["latency_ms"]
    lines += ["", f"Guard latency (no LLM), {lt['machine']}, n={lt['n']}: p50 {lt['p50']} ms, p95 {lt['p95']} ms."]
    (OUT / "detector_eval.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
