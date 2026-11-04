"""Process-local sliding-window rate limiting.

Deliberately simple: one API process is the deployment target for v1. When the
API is scaled horizontally this must move to Redis (see docs/DECISIONS.md).
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            # Opportunistic cleanup to bound memory for abandoned keys.
            if len(self._hits) > 10_000:
                for stale_key in [k for k, v in self._hits.items() if not v]:
                    del self._hits[stale_key]
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_key(request: Request) -> str:
    # request.client is None only for synthetic ASGI scopes (tests).
    host = request.client.host if request.client else "unknown"
    return host


def rate_limit(scope: str, limit: int, window_seconds: int = 60):
    """Dependency factory. `limit` is read from settings by the caller."""

    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED or settings.APP_ENV == "test":
            return
        if not limiter.allow(f"{scope}:{client_key(request)}", limit, window_seconds):
            raise AppError(
                "Too many requests. Please wait a moment and try again.",
                code="rate_limited",
                status_code=429,
            )

    return dependency
