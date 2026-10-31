"""Runs on the GPU box. Standard library only.

  python3 run_reviews.py            # every model in models.txt
Writes reviews.jsonl (one line per model x prompt, resumable) and run_meta.json.
Same settings as the CommentInject promptfoo config: temperature 0, num_predict 128.
"""
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
HERE = os.path.dirname(os.path.abspath(__file__))
THREADS = int(os.environ.get("THREADS", "4"))


def gen(model, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 128, "seed": 0}}).encode()
    req = urllib.request.Request(HOST + "/api/generate", body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return d.get("response", ""), round((time.time() - t0) * 1000, 1), d.get("prompt_eval_count", 0), d.get("eval_count", 0)


def main():
    models = [m.strip() for m in open(os.path.join(HERE, "models.txt")) if m.strip()]
    prompts = [json.loads(l) for l in open(os.path.join(HERE, "prompts.jsonl"))]
    out_path = os.path.join(HERE, "reviews.jsonl")
    done = set()
    if os.path.exists(out_path):
        for l in open(out_path):
            d = json.loads(l)
            done.add((d["model"], d["id"]))
    meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "host": platform.node(), "threads": THREADS, "models": {}}
    try:
        meta["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                     capture_output=True, text=True).stdout.strip()
    except OSError:
        meta["gpu"] = "unknown"
    with open(out_path, "a") as out:
        for m in models:
            subprocess.run(["ollama", "pull", m], check=False)
            todo = [p for p in prompts if (m, p["id"]) not in done]
            gen(m, "Say OK.")  # load the model before timing
            t0 = time.time()

            def one(p):
                text, ms, tin, tout = gen(m, p["prompt"])
                return {"model": m, "id": p["id"], "response": text, "ms": ms, "in": tin, "out": tout}

            n = 0
            with ThreadPoolExecutor(THREADS) as ex:
                for rec in ex.map(one, todo):
                    out.write(json.dumps(rec) + "\n")
                    n += 1
                    if n % 200 == 0:
                        out.flush()
                        print(f"{m}: {n}/{len(todo)}", flush=True)
            meta["models"][m] = {"calls": n, "wall_s": round(time.time() - t0, 1)}
            print(f"{m}: done, {n} calls, {meta['models'][m]['wall_s']} s", flush=True)
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    json.dump(meta, open(os.path.join(HERE, "run_meta.json"), "w"), indent=2)
    print("ALL DONE. Download reviews.jsonl and run_meta.json.")


if __name__ == "__main__":
    sys.exit(main())
