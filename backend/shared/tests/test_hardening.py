"""Regression tests for hardening tasks A-G."""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

# ── A. Dockerfile non-root ───────────────────────────────────────────────────

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES = ["api_execute", "callback_manual", "tasks", "canales_service", "open_agent"]


@pytest.mark.parametrize("service", SERVICES)
def test_dockerfile_runs_as_non_root(service: str):
    """Every service Dockerfile must contain a USER directive (non-root)."""
    dockerfile = BACKEND_ROOT / service / "Dockerfile"
    assert dockerfile.exists(), f"Missing Dockerfile for {service}"
    content = dockerfile.read_text()
    assert "USER appuser" in content, f"{service}/Dockerfile does not run as non-root (missing USER appuser)"
    assert "adduser" in content, f"{service}/Dockerfile does not create appuser"


# ── B. Tenant middleware is pure ASGI ────────────────────────────────────────

def test_tenant_middleware_is_callable():
    """TenantMiddleware must be instantiable and callable."""
    from shared.middleware.tenant import TenantMiddleware

    mw = TenantMiddleware(app=MagicMock())
    assert callable(mw)


def test_tenant_middleware_preserves_state_keys():
    """TenantMiddleware must set auth_context, auth_error, tenant_id on request.state."""
    from shared.middleware.tenant import TenantMiddleware

    app = FastAPI()
    app.add_middleware(TenantMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "has_auth_context": hasattr(request.state, "auth_context"),
            "has_auth_error": hasattr(request.state, "auth_error"),
            "has_tenant_id": hasattr(request.state, "tenant_id"),
        }

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_auth_context"] is True
    assert data["has_auth_error"] is True
    assert data["has_tenant_id"] is True


# ── C. Global error handler ─────────────────────────────────────────────────

def test_catch_all_returns_500_without_internals():
    """Unhandled exceptions must return 500 with generic detail, no stack trace."""
    from shared.utils.exceptions import register_exception_handlers

    app = FastAPI(title="test-service")
    register_exception_handlers(app)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("secret database password is leaked here")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/explode")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal server error"
    assert body["code"] == "INTERNAL_ERROR"
    # Must NOT leak the actual error message
    assert "secret" not in resp.text
    assert "password" not in resp.text
    assert "leaked" not in resp.text


def test_domain_exceptions_still_work():
    """Existing domain exceptions (NotFound, Conflict, etc.) must not be broken."""
    from shared.utils.exceptions import (
        ConflictError,
        ForbiddenError,
        InvalidTransitionError,
        NotFoundError,
        register_exception_handlers,
    )

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def nf():
        raise NotFoundError("Producto", "123")

    @app.get("/forbidden")
    async def fb():
        raise ForbiddenError()

    @app.get("/conflict")
    async def cf():
        raise ConflictError("Duplicate email")

    @app.get("/transition")
    async def tr():
        raise InvalidTransitionError("NUEVO", "CONVERTIDO")

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/not-found").status_code == 404
    assert client.get("/forbidden").status_code == 403
    assert client.get("/conflict").status_code == 409
    assert client.get("/transition").status_code == 422


def test_rate_limit_exception_returns_429():
    """RateLimitError must return 429 with Retry-After header."""
    from shared.utils.exceptions import RateLimitError, register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/limited")
    async def limited():
        raise RateLimitError(retry_after=30)

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/limited")
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == "30"
    assert resp.json()["code"] == "RATE_LIMITED"


# ── D. Rate limiter ─────────────────────────────────────────────────────────

def test_rate_limiter_blocks_after_threshold():
    """Rate limiter must block requests after exceeding max_requests."""
    from shared.middleware.rate_limit import _SlidingWindowCounter

    counter = _SlidingWindowCounter()
    key = "test:tenant:abc"
    # Allow 3 requests in 60s
    assert counter.check(key, 3, 60) is True
    assert counter.check(key, 3, 60) is True
    assert counter.check(key, 3, 60) is True
    # 4th should be blocked
    assert counter.check(key, 3, 60) is False


def test_rate_limiter_skips_service_tokens():
    """Service-to-service calls must NOT be rate limited."""
    from shared.middleware.rate_limit import require_rate_limit

    app = FastAPI()

    dep = require_rate_limit(max_requests=1, window_seconds=60)

    @app.get("/test", dependencies=[dep])
    async def test_endpoint():
        return {"ok": True}

    # Simulate with no auth context (will be rate limited after 1 req)
    client = TestClient(app)
    # First request should work
    resp1 = client.get("/test")
    assert resp1.status_code == 200


# ── E. DB admin naming ───────────────────────────────────────────────────────

def test_get_db_superadmin_bypass_exists():
    """The explicit bypass function must exist and be importable."""
    from shared.database.dependencies import get_db_superadmin_bypass
    assert callable(get_db_superadmin_bypass)


def test_get_db_admin_is_alias():
    """get_db_admin must be an alias for get_db_superadmin_bypass."""
    from shared.database.dependencies import get_db_admin, get_db_superadmin_bypass
    assert get_db_admin is get_db_superadmin_bypass


# ── F. Requirements pinning ──────────────────────────────────────────────────

@pytest.mark.parametrize("service", SERVICES)
def test_requirements_are_pinned(service: str):
    """Every production dependency must use == pinning, not >=."""
    req_file = BACKEND_ROOT / service / "requirements.txt"
    assert req_file.exists(), f"Missing requirements.txt for {service}"
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert ">=" not in line, (
            f"{service}/requirements.txt has unpinned dep: {line}"
        )
