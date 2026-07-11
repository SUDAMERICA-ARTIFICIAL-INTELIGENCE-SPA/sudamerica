"""Request ID middleware for FastAPI services."""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """Return the current request id or a placeholder when outside a request context."""
    return request_id_ctx_var.get() or "no-request"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach/propagate X-Request-ID for every request and store it in ContextVar."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("x-request-id")
        request_id = incoming or str(uuid.uuid4())

        token = request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
