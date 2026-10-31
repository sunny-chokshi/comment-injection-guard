"""API keys, per-key rate limit and a hard monthly spend cap.

The rate limiter is in memory, so it is per instance. Run one instance, or
put a shared store behind it before scaling out.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path


def load_keys() -> list[str]:
    return [k.strip() for k in os.environ.get("GUARD_API_KEYS", "").split(",") if k.strip()]


def check_key(given: str | None, keys: list[str]) -> bool:
    if not given or not keys:
        return False  # fail closed when no keys are configured
    return any(hmac.compare_digest(given.encode(), k.encode()) for k in keys)


def key_id(key: str | None) -> str:
    return hashlib.sha256((key or "").encode()).hexdigest()[:10]


class RateLimiter:
    def __init__(self, per_minute: int):
        self.rate = per_minute / 60.0
        self.cap = float(per_minute)
        self.buckets: dict[str, tuple[float, float]] = {}
        self.lock = threading.Lock()

    def allow(self, who: str) -> bool:
        now = time.monotonic()
        with self.lock:
            tokens, last = self.buckets.get(who, (self.cap, now))
            tokens = min(self.cap, tokens + (now - last) * self.rate)
            if tokens < 1:
                self.buckets[who] = (tokens, now)
                return False
            self.buckets[who] = (tokens - 1, now)
            return True


class SpendCap:
    """Tracks reviewer spend per calendar month (UTC) in a JSON file.

    Before each paid call it reserves the worst case (prompt estimate plus
    max output tokens). If the reservation would cross the cap, the call is
    refused. After the call the reservation is replaced by the real cost.
    """

    def __init__(self, cap_usd: float, price_in: float | None, price_out: float | None, path: Path):
        self.cap, self.p_in, self.p_out, self.path = cap_usd, price_in, price_out, path
        self.lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "SpendCap":
        def f(name):
            v = os.environ.get(name)
            return float(v) if v else None
        return cls(f("MONTHLY_CAP_USD") or 0.0, f("REVIEWER_PRICE_IN_PER_MTOK"), f("REVIEWER_PRICE_OUT_PER_MTOK"),
                   Path(os.environ.get("SPEND_FILE", "/tmp/guard_spend.json")))

    @property
    def configured(self) -> bool:
        return self.cap > 0 and self.p_in is not None and self.p_out is not None

    def cost(self, tok_in: int, tok_out: int) -> float:
        return (tok_in * (self.p_in or 0) + tok_out * (self.p_out or 0)) / 1e6

    def _month(self) -> str:
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def spent(self) -> float:
        return float(self._read().get(self._month(), 0.0))

    def reserve(self, est_in: int, max_out: int) -> float | None:
        need = self.cost(est_in, max_out)
        with self.lock:
            d = self._read()
            m = self._month()
            if d.get(m, 0.0) + need > self.cap:
                return None
            d[m] = d.get(m, 0.0) + need
            self.path.write_text(json.dumps(d))
        return need

    def settle(self, reserved: float, tok_in: int, tok_out: int) -> float:
        actual = self.cost(tok_in, tok_out)
        with self.lock:
            d = self._read()
            m = self._month()
            d[m] = max(0.0, d.get(m, 0.0) - reserved + actual)
            self.path.write_text(json.dumps(d))
        return actual
