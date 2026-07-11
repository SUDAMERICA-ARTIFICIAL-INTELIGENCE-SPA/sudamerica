"""Structured JSON logging utilities shared across services."""

import json
import logging
import sys
from datetime import datetime, timezone
from types import TracebackType
from typing import Any

from shared.middleware.request_id import get_request_id


def _utc_iso(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for Cloud Logging ingestion."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "timestamp": _utc_iso(),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "tenant_id": getattr(record, "tenant_id", None),
            "path": getattr(record, "path", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "extra": getattr(record, "extra", None),
        }

        # Include exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            payload["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configure root logger to output JSON to stdout and return the service logger."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers on reload
    has_json_handler = any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JsonFormatter) for h in root.handlers)
    if not has_json_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter(service_name))
        root.handlers = [handler]

    logger = logging.getLogger(service_name)
    logger.propagate = True
    return logger


def get_logger(service_name: str, level: str = "INFO") -> logging.Logger:
    """Return a logger configured with JSON formatter; idempotent."""
    return configure_logging(service_name, level)
