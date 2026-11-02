"""Per-IP limits on login and sign-up tries (ARCH-031), on top of the account lockout (SAFE-022).

One replica (ARCH-010), so the counts live in memory. A deploy starts them over, which is fine.
"""

import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

# ARCH-031 limits are per minute. The limits themselves come from config (AI-013).
WINDOW_SECONDS = 60
LIMIT_KEYS = {
    "login": "login_ip_limit_per_minute",
    "staff_login": "login_ip_limit_per_minute",
    "signup": "signup_ip_limit_per_minute",
}
STATUS = 429
CODE = "RATE_LIMITED"
MESSAGE = "Too many tries. Wait a minute and try again."


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._last_sweep = clock()

    def allow(self, kind: str, ip: str, limit: int) -> bool:
        """Count one try. False once this IP has had `limit` tries in the last minute.

        A refused try is not counted, so each IP gets exactly `limit` tries per minute.
        """
        now = self._clock()
        cutoff = now - WINDOW_SECONDS
        with self._lock:
            if now - self._last_sweep > WINDOW_SECONDS:
                self._sweep(cutoff)
                self._last_sweep = now
            hits = self._hits.setdefault((kind, ip), deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def _sweep(self, cutoff: float) -> None:
        # Drop IPs with no recent tries, so memory stays small while Wrapped is open all year.
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= cutoff]:
            del self._hits[key]


def client_ip(request: Request) -> str:
    # Railway's edge sets X-Real-IP to the address it saw and replaces any value the phone sent.
    # X-Forwarded-For's last entry is a rotating edge node, so it can't be used (checked on PR 71).
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    return request.client.host if request.client else "unknown"


def allow(request: Request, kind: str) -> bool:
    limit = request.app.state.config["auth"][LIMIT_KEYS[kind]]
    return request.app.state.rate_limiter.allow(kind, client_ip(request), limit)
