"""Build a self-contained bundle for running the reviewer eval on a GPU box.

The guard runs here; the bundle carries the already-guarded code, so the GPU
box needs only Python 3 (standard library) and Ollama.

  python eval/make_pod_bundle.py      ->  results/pod_bundle.tgz
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from guard.core import Guard  # noqa: E402
from guard.reviewer import REVIEW_PROMPT  # noqa: E402

MODELS = ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]


def main():
    guards = {"guard_flagged": Guard("either", "strip_flagged"), "strip_all": Guard("regex", "strip_all")}
    samples = [json.loads(l) for l in (ROOT / "data/external/commentinject/samples.jsonl").open()]
    rows = [{"set": "clean", "label": 1, "strategy": "clean", "sample": s["id"], "code": s["code"]} for s in samples]
    for f in ("snippets_test.jsonl", "snippets_adaptive.jsonl"):
        rows += [json.loads(l) for l in (ROOT / "data" / f).open()]

    prompts, items = {}, []
    for i, r in enumerate(rows):
        variants = {"unguarded": r["code"]}
        for g, gd in guards.items():
            variants[g] = gd.scan(r["code"], "python").guarded_code
        ids = {}
        for v, code in variants.items():
            pid = hashlib.sha256(code.encode()).hexdigest()[:16]
            prompts[pid] = REVIEW_PROMPT.format(code=code)
            ids[v] = pid
        items.append({"i": i, "set": r["set"], "strategy": r["strategy"], "sample": r["sample"],
                      "vulnerable": True, "prompt_ids": ids})

    out = ROOT / "results" / "pod_bundle"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    with (out / "prompts.jsonl").open("w") as f:
        for pid, p in prompts.items():
            f.write(json.dumps({"id": pid, "prompt": p}) + "\n")
    (out / "items.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items))
    (out / "models.txt").write_text("\n".join(MODELS) + "\n")
    shutil.copy(ROOT / "eval" / "pod_run_reviews.py", out / "run_reviews.py")
    tgz = ROOT / "results" / "pod_bundle.tgz"
    with tarfile.open(tgz, "w:gz") as t:
        t.add(out, arcname="guard_eval")
    md5 = hashlib.md5(tgz.read_bytes()).hexdigest()
    print(f"{len(items)} snippets, {len(prompts)} unique prompts per model, {len(MODELS)} models")
    print(f"{tgz}  {tgz.stat().st_size // 1024} KB  md5 {md5}")


if __name__ == "__main__":
    main()
