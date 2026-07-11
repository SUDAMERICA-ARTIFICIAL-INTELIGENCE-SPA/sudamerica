"""Custom exceptions and FastAPI exception handlers."""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: str | None = None):
        self.resource = resource
        self.identifier = identifier
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(detail)


class ForbiddenError(Exception):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(detail)


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Invalid transition from {current} to {target}")
        self.current = current
        self.target = target


class ConflictError(Exception):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(detail)


class RateLimitError(Exception):
    """Raised when a tenant exceeds their rate limit."""

    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc), "code": "NOT_FOUND"})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(status_code=403, content={"detail": str(exc), "code": "FORBIDDEN"})

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition_handler(request: Request, exc: InvalidTransitionError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "code": "INVALID_TRANSITION"},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc), "code": "CONFLICT"})

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc), "code": "RATE_LIMITED"},
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(Exception)
    async def catch_all_handler(request: Request, exc: Exception):
        service_name = getattr(getattr(request, "app", None), "title", "unknown")
        tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
        logger.error(
            "Unhandled exception | service=%s path=%s method=%s tenant=%s",
            service_name,
            request.url.path,
            request.method,
            tenant_id,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
        )
