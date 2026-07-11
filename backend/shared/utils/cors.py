"""Shared CORS helpers for frontend-facing services."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "https://sudamerica.ai",
    "https://app.sudamerica.ai",
)
FRONTEND_CLOUD_RUN_REGEX = r"^https://(frontend|sudamerica-admin)-[a-z0-9-]+\.[a-z0-9.-]+\.run\.app$"


def add_frontend_cors(app: FastAPI, frontend_url: str | None) -> None:
    """Apply the shared frontend CORS policy to a FastAPI app."""
    origins = list(DEFAULT_CORS_ORIGINS)
    normalized = _normalize_origin(frontend_url)
    if normalized and normalized not in origins:
        origins.append(normalized)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=FRONTEND_CLOUD_RUN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _normalize_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    return origin.rstrip("/")
