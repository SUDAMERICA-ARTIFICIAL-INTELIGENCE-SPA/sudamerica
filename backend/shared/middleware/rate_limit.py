"""In-memory tenant-aware rate limiter using sliding window counters.

Usage in routes:
    from shared.middleware.rate_limit import require_rate_limit

    @router.post("/chat")
    async def chat(
        request: Request,
        _rl=Depends(require_rate_limit(max_requests=20, window_seconds=60)),
    ):
        ...
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, Request

from shared.utils.exceptions import RateLimitError


class _SlidingWindowCounter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._windows[key]
            # Prune expired entries
            self._windows[key] = [t for t in timestamps if t > cutoff]
            if len(self._windows[key]) >= max_requests:
                return False
            self._windows[key].append(now)
            return True


# Global singleton — survives across requests within one process
_limiter = _SlidingWindowCounter()


def _get_rate_limit_key(request: Request) -> str:
    """Build a rate limit key from tenant_id (preferred) or client IP."""
    tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
    if tenant_id:
        return f"tenant:{tenant_id}"
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


def require_rate_limit(max_requests: int = 30, window_seconds: int = 60):
    """FastAPI dependency that enforces per-tenant rate limiting.

    Skips rate limiting for internal service-to-service calls.
    """

    def _dependency(request: Request) -> None:
        # Skip rate limiting for service tokens (inter-service calls)
        auth_ctx = getattr(getattr(request, "state", None), "auth_context", None)
        if auth_ctx and auth_ctx.get("type") == "service":
            return

        key = f"{_get_rate_limit_key(request)}:{request.url.path}"
        if not _limiter.check(key, max_requests, window_seconds):
            raise RateLimitError(
                detail="Too many requests, please try again later",
                retry_after=window_seconds,
            )

    return Depends(_dependency)
