"""HTTP client wrapper with retry and header injection."""

import asyncio
import json
import logging
import random
import time

import httpx

from shared.middleware.request_id import get_request_id

logger = logging.getLogger(__name__)

# ── Pooled httpx.AsyncClient singleton ───────────────────────────────
# One connection pool (keep-alive) reused across all inter-service requests,
# instead of opening a fresh client + TCP/TLS handshake per call. Created
# lazily on first use inside the running event loop; closed on app shutdown
# via aclose_pooled_client() (wired into the FastAPI lifespan).
_pooled_client: httpx.AsyncClient | None = None


def get_pooled_client() -> httpx.AsyncClient:
    """Return the shared pooled AsyncClient, creating it on first use."""
    global _pooled_client
    if _pooled_client is None:
        _pooled_client = httpx.AsyncClient(
            # No http2: targets are uvicorn (HTTP/1.1), so it would negotiate down
            # anyway; the latency win is the keep-alive pool, and this avoids the
            # optional `h2` dependency that is not pinned in requirements.
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            timeout=30.0,
        )
    return _pooled_client


async def aclose_pooled_client() -> None:
    """Close the shared pooled client. Call once on app shutdown."""
    global _pooled_client
    if _pooled_client is not None:
        await _pooled_client.aclose()
        _pooled_client = None


class HttpClient:
    """Async HTTP client with retry logic and tenant header injection."""

    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        # Only retry idempotent methods (GET, PUT, DELETE) on ReadTimeout.
        # POST is not idempotent — retrying can cause duplicate side effects.
        retry_on_timeout = method.upper() in {"GET", "PUT", "DELETE", "HEAD", "OPTIONS"}
        retryable = (httpx.ConnectError, httpx.ReadTimeout) if retry_on_timeout else (httpx.ConnectError,)
        last_exc = None

        merged_headers = {**(headers or {})}
        request_id = get_request_id()
        if request_id and request_id != "no-request":
            merged_headers["X-Request-ID"] = request_id

        # Reuse the shared pooled client; default to this wrapper's timeout
        # unless the caller overrode it per-call (e.g. post(..., timeout=60.0)).
        kwargs.setdefault("timeout", self.timeout)
        client = get_pooled_client()
        start = time.monotonic()
        for attempt in range(self.max_retries):
            try:
                resp = await client.request(method, url, headers=merged_headers, **kwargs)
                # Surface slow inter-service calls (cold connect / slow peer) that
                # would otherwise be invisible — a leading pre-LLM latency suspect.
                elapsed = time.monotonic() - start
                if elapsed > 2.0:
                    logger.warning("HTTP_SLOW %s", json.dumps(
                        {"method": method.upper(), "url": url,
                         "elapsed_s": round(elapsed, 2), "attempts": attempt + 1}))
                return resp
            except retryable as exc:
                last_exc = exc
                if attempt == self.max_retries - 1:
                    raise
                backoff = min(2 ** attempt, 8) + random.uniform(0, 0.25)
                # Retries were previously SILENT — log so a ~5s stall from a
                # ConnectError/ReadTimeout + backoff is visible in production.
                logger.warning("HTTP_RETRY %s", json.dumps(
                    {"method": method.upper(), "url": url, "attempt": attempt + 1,
                     "exc": type(exc).__name__, "backoff_s": round(backoff, 2)}))
                await asyncio.sleep(backoff)
            except httpx.ReadTimeout:
                raise
        raise last_exc  # type: ignore[misc]

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)


# Shared singleton for inter-service calls.
# Backed by one pooled httpx.AsyncClient (see get_pooled_client) reused across
# all calls. Callers can override timeout per-request via kwargs: post(url, timeout=60.0).
internal_http = HttpClient(base_url="", timeout=10.0)
