"""FastAPI service.

POST /v1/scan   flag steering comments; optionally run the reviewer on the
                raw and guarded code and return both verdicts.
GET  /health    liveness, no auth.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .core import Guard
from .limits import RateLimiter, SpendCap, check_key, key_id, load_keys
from .reviewer import get_reviewer

MAX_CODE_BYTES = int(os.environ.get("MAX_CODE_BYTES", 64_000))
MAX_OUT_TOKENS = 1024

log = logging.getLogger("guard")
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.INFO)

app = FastAPI(title="Comment-Injection Guard", version="0.1.0")
_state: dict = {}


def state() -> dict:
    if not _state:
        _state["guard"] = Guard(detector=os.environ.get("GUARD_DETECTOR", "either"),
                                mode=os.environ.get("GUARD_MODE", "strip_all"))
        _state["keys"] = load_keys()
        _state["rl"] = RateLimiter(int(os.environ.get("RATE_PER_MIN", 30)))
        _state["cap"] = SpendCap.from_env()
        _state["reviewer"] = get_reviewer()
    return _state


class ScanIn(BaseModel):
    code: str = Field(..., description="Snippet, file or diff hunk")
    language: str | None = Field(None, description="python, c, cpp, java, js, go. Guessed if omitted")
    review: bool = Field(False, description="Also run the LLM reviewer on raw and guarded code")


def auth(request: Request, x_api_key: str | None = Header(None)) -> str:
    s = state()
    if not check_key(x_api_key, s["keys"]):
        raise HTTPException(401, "missing or invalid X-API-Key")
    kid = key_id(x_api_key)
    if not s["rl"].allow(kid):
        raise HTTPException(429, "rate limit")
    request.state.kid = kid
    return kid


@app.get("/health")
def health():
    s = state()
    return {"status": "ok", "detector": s["guard"].detector, "mode": s["guard"].mode,
            "reviewer": type(s["reviewer"]).__name__ if s["reviewer"] else None}


@app.post("/v1/scan")
def scan(body: ScanIn, request: Request, kid: str = Depends(auth)):
    t0 = time.perf_counter()
    if len(body.code.encode()) > MAX_CODE_BYTES:
        raise HTTPException(413, f"code larger than {MAX_CODE_BYTES} bytes")
    s = state()
    res = s["guard"].scan(body.code, body.language)
    out = res.to_dict()
    guard_ms = (time.perf_counter() - t0) * 1000
    cost = 0.0
    if body.review:
        rv = s["reviewer"]
        if rv is None:
            raise HTTPException(400, "reviewer not configured on this deployment")
        reserved = 0.0
        if rv.paid:
            if not s["cap"].configured:
                raise HTTPException(503, "paid reviewer needs MONTHLY_CAP_USD and price env vars")
            est_in = 2 * (len(body.code) // 3 + 200)  # rough: two calls, ~3 chars per token
            reserved = s["cap"].reserve(est_in, 2 * MAX_OUT_TOKENS)
            if reserved is None:
                raise HTTPException(402, "monthly spend cap reached")
        raw = rv.review(body.code)
        guarded = rv.review(res.guarded_code) if res.guarded_code != body.code else raw
        if rv.paid:
            tin = raw.input_tokens + (guarded.input_tokens if guarded is not raw else 0)
            tout = raw.output_tokens + (guarded.output_tokens if guarded is not raw else 0)
            cost = s["cap"].settle(reserved, tin, tout)
        out["verdict_unguarded"] = raw.verdict
        out["verdict_guarded"] = guarded.verdict
        out["reviewer_model"] = raw.model
    total_ms = (time.perf_counter() - t0) * 1000
    out["latency_ms"] = {"guard": round(guard_ms, 2), "total": round(total_ms, 2)}
    # Never log code or comment text: only sizes, hashes and counts.
    log.info(json.dumps({"ts": time.time(), "key": kid, "path": "/v1/scan",
                         "code_sha": hashlib.sha256(body.code.encode()).hexdigest()[:12],
                         "bytes": len(body.code), "n_comments": res.n_comments, "n_flags": len(res.flags),
                         "review": body.review, "cost_usd": round(cost, 6),
                         "guard_ms": round(guard_ms, 2), "total_ms": round(total_ms, 2)}))
    return out
