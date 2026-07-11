"""Test fixtures for open_agent."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set required env vars before importing settings
os.environ.setdefault("JWT_SECRET_KEY", "a" * 64)
os.environ.setdefault("OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY", "b" * 64)


@pytest.fixture
def settings():
    from app.config import OpenAgentSettings
    return OpenAgentSettings(
        JWT_SECRET_KEY="a" * 64,
        OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY="b" * 64,
        OPENAI_API_KEY="test-key",
    )


@pytest.fixture
def mock_http_client():
    """Return a mock httpx.AsyncClient."""
    client = AsyncMock()
    return client
