"""
GCRA (Generic Cell Rate Algorithm) rate limiter, applied per client IP to
`/analyze` and `/jobs/{id}/chat` — the two endpoints that spend Gemini free-
tier quota. That quota is shared across every visitor hitting one deployed
instance (Google's rate limits are per-project, not per-caller), so without
this a handful of concurrent users can lock everyone out with 429s from
Gemini itself. Better to fail fast with a clear "slow down" from our own API.

GCRA over a plain fixed-window or leaky-bucket counter because it needs no
background timer or cleanup sweep: each key's state is a single float (its
"theoretical arrival time"), rate limiting falls out of comparing it to the
current time, and it naturally allows a small configurable burst on top of
the steady rate — which matters here since a page refresh right after a
first request shouldn't itself be rate limited.
"""
import time
from threading import Lock
from typing import Dict, Tuple


class GCRARateLimiter:
    def __init__(self, rate: int, period_seconds: float, burst: int = 1):
        """
        Allows `rate` requests per `period_seconds`, with up to `burst` requests
        able to fire back-to-back before the steady-state spacing kicks in.
        """
        if rate <= 0 or period_seconds <= 0 or burst < 1:
            raise ValueError("rate and period_seconds must be positive; burst must be >= 1")
        self.emission_interval = period_seconds / rate
        self.burst_offset = self.emission_interval * (burst - 1)
        self._tat: Dict[str, float] = {}  # key -> theoretical arrival time
        self._lock = Lock()

    def allow(self, key: str) -> Tuple[bool, float]:
        """Returns (allowed, retry_after_seconds). retry_after is 0.0 when allowed."""
        now = time.monotonic()
        with self._lock:
            tat = max(self._tat.get(key, now), now)
            allow_at = tat - self.burst_offset
            if allow_at > now:
                return False, allow_at - now
            self._tat[key] = tat + self.emission_interval
            return True, 0.0

    def reset(self, key: str) -> None:
        """Test/debug hook — not used in the request path."""
        with self._lock:
            self._tat.pop(key, None)
