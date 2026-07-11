"""Tenant middleware that derives tenant context only from validated auth."""

import logging

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.middleware.auth import resolve_request_auth_context

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve authenticated tenant context before FastAPI dependencies run."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.auth_context = None
        request.state.auth_error = None
        request.state.tenant_id = None

        try:
            auth_context = resolve_request_auth_context(request)
        except HTTPException as exc:
            request.state.auth_error = exc
        except Exception as exc:
            logger.warning("Unexpected auth error: %s", exc, exc_info=True)
            request.state.auth_error = HTTPException(
                status_code=401, detail="Authentication failed",
            )
        else:
            request.state.auth_context = auth_context
            if auth_context is not None:
                request.state.tenant_id = auth_context["tenant_id"]

        return await call_next(request)
