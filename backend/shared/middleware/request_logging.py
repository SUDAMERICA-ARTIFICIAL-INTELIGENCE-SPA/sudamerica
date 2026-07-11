"""Request logging middleware emitting structured JSON logs."""

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.middleware.request_id import get_request_id


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log start/end/error for every request with request_id and tenant context."""

    def __init__(self, app, service_name: str, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        request_id = get_request_id()
        tenant_id = getattr(request.state, "tenant_id", None)
        path = request.url.path
        method = request.method

        self.logger.info(
            "request started",
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "path": path,
                "method": method,
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self.logger.error(
                "request failed",
                extra={
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "path": path,
                    "method": method,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        status = response.status_code
        level = logging.INFO if status < 400 else logging.WARNING if status < 500 else logging.ERROR

        self.logger.log(
            level,
            "request completed",
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "path": path,
                "method": method,
                "status_code": status,
                "duration_ms": duration_ms,
            },
        )

        return response
