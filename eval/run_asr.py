"""End-to-end: attack success rate against a real LLM reviewer, with and without the guard.

ASR here = share of vulnerable samples the reviewer calls SAFE. Clean ASR is the
reviewer's own miss rate with no attack, so read the attacked rows against it.

Costs money or GPU time. Examples:
  REVIEWER_BACKEND=ollama REVIEWER_MODEL=qwen2.5-coder:7b python eval/run_asr.py
  REVIEWER_BACKEND=anthropic REVIEWER_MODEL=claude-opus-5-5 python eval/run_asr.py \
      --price-in <USD per Mtok> --price-out <USD per Mtok> --limit 60
Prices are not hard-coded; copy them from the provider's pricing page on the day you run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from guard.core import Guard  # noqa: E402
from guard.reviewer import get_reviewer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=None)
    ap.add_argument("--limit", type=int, default=0, help="cap snippets per set (0 = all)")
    ap.add_argument("--price-in", type=float, default=None)
    ap.add_argument("--price-out", type=float, default=None)
    ap.add_argument("--out", default=str(ROOT / "results" / "asr.json"))
    a = ap.parse_args()

    rv = get_reviewer(a.backend)
    if rv is None:
        sys.exit("set REVIEWER_BACKEND or --backend (mock, ollama, anthropic)")
    guards = {"guard_flagged": Guard("either", "strip_flagged"), "strip_all": Guard("regex", "strip_all")}

    samples = [json.loads(l) for l in (ROOT / "data/external/commentinject/samples.jsonl").open()]
    sets = {"clean": [{"code": s["code"], "strategy": "clean"} for s in samples]}
    for f in ("snippets_test.jsonl", "snippets_adaptive.jsonl"):
        for r in map(json.loads, (ROOT / "data" / f).open()):
            if r["label"] == 1:
                sets.setdefault(r["set"], []).append(r)
    if a.limit:
        sets = {k: v[:a.limit] for k, v in sets.items()}

    tok_in = tok_out = calls = 0
    res = {}
    for name, rows in sets.items():
        c = {"n": len(rows), "unguarded_safe": 0, "guard_flagged_safe": 0, "strip_all_safe": 0}
        for r in rows:
            cache = {}
            for label, code in [("unguarded", r["code"])] + [(g, gd.scan(r["code"], "python").guarded_code)
                                                              for g, gd in guards.items()]:
                if code not in cache:
                    rev = rv.review(code)
                    cache[code] = rev
                    tok_in, tok_out, calls = tok_in + rev.input_tokens, tok_out + rev.output_tokens, calls + 1
                c[f"{label}_safe"] += cache[code].verdict == "SAFE"
        for k in ("unguarded", "guard_flagged", "strip_all"):
            c[f"asr_{k}"] = round(c[f"{k}_safe"] / c["n"], 4) if c["n"] else None
        res[name] = c
        print(name, c, flush=True)

    out = {"backend": type(rv).__name__, "model": getattr(rv, "model", "mock"), "sets": res,
           "llm_calls": calls, "input_tokens": tok_in, "output_tokens": tok_out}
    if a.price_in is not None and a.price_out is not None and calls:
        cost = (tok_in * a.price_in + tok_out * a.price_out) / 1e6
        # One guarded request = one or two reviewer calls; report per reviewer call and per guarded request.
        out["cost_usd_total"] = round(cost, 4)
        out["cost_per_1000_reviewer_calls"] = round(1000 * cost / calls, 4)
        out["cost_per_1000_guarded_requests_upper"] = round(2000 * cost / calls, 4)
    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
