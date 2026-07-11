"""Tests for email sending route — all SMTP interactions mocked."""

from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest


@pytest.mark.asyncio
async def test_send_email_success(client, auth_headers, mock_smtp):
    """Authenticated email send returns success."""
    body = {
        "to": "cliente@example.com",
        "subject": "Cotizacion",
        "body": "Adjunto la cotizacion solicitada.",
        "html": "<p>Adjunto la cotizacion solicitada.</p>",
    }
    with patch("app.services.email_service.aiosmtplib.send", mock_smtp):
        response = await client.post(
            "/api/v1/tasks/email/send", json=body, headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_send_email_plain_text(client, auth_headers, mock_smtp):
    """Email without HTML body still sends successfully."""
    body = {
        "to": "cliente@example.com",
        "subject": "Seguimiento",
        "body": "Le escribo para dar seguimiento.",
    }
    with patch("app.services.email_service.aiosmtplib.send", mock_smtp):
        response = await client.post(
            "/api/v1/tasks/email/send", json=body, headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_send_email_requires_auth(client):
    """Email endpoint rejects unauthenticated requests."""
    body = {
        "to": "cliente@example.com",
        "subject": "Test",
        "body": "Test body",
    }
    response = await client.post("/api/v1/tasks/email/send", json=body)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_send_email_smtp_failure(client, auth_headers):
    """SMTP failure returns success=false, does not raise 500."""
    body = {
        "to": "cliente@example.com",
        "subject": "Test",
        "body": "Test body",
    }
    mock_fail = AsyncMock(side_effect=aiosmtplib.SMTPException("SMTP connection refused"))
    with patch("app.services.email_service.aiosmtplib.send", mock_fail):
        response = await client.post(
            "/api/v1/tasks/email/send", json=body, headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["success"] is False
