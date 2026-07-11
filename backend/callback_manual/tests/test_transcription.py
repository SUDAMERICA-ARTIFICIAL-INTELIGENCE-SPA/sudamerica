"""Tests for transcription endpoint with mocked Whisper API."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.transcription_service import DownloadedAudio


@pytest.mark.asyncio
@patch("app.services.transcription_service._call_whisper", new_callable=AsyncMock)
@patch("app.services.transcription_service._download_audio", new_callable=AsyncMock)
async def test_transcribe_audio(
    mock_download, mock_whisper, client, auth_headers
):
    """POST /api/v1/transcription returns transcribed text."""
    mock_download.return_value = DownloadedAudio(
        filename="audio.ogg",
        content_type="audio/ogg",
        content=b"fake-audio-bytes",
    )
    mock_whisper.return_value = ("Hola, quiero cotizar un producto.", 3.45)

    payload = {"audio_url": "https://example.com/audio.ogg"}
    response = await client.post(
        "/api/v1/transcription", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Hola, quiero cotizar un producto."
    assert body["duration_seconds"] == pytest.approx(3.45, abs=0.01)
    mock_download.assert_awaited_once_with("https://example.com/audio.ogg")
    mock_whisper.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.transcription_service._call_whisper", new_callable=AsyncMock)
@patch("app.services.transcription_service._download_audio", new_callable=AsyncMock)
async def test_transcribe_legacy_alias(
    mock_download, mock_whisper, client, auth_headers
):
    mock_download.return_value = DownloadedAudio(
        filename="audio.ogg",
        content_type="audio/ogg",
        content=b"fake-audio-bytes",
    )
    mock_whisper.return_value = ("Texto legado.", 1.2)

    response = await client.post(
        "/api/v1/reviews/transcription",
        json={"audio_url": "https://example.com/audio.ogg"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Texto legado."


@pytest.mark.asyncio
async def test_transcribe_no_api_key(client, auth_headers):
    """POST /api/v1/transcription returns 503 when OPENAI_API_KEY is empty."""
    # Temporarily set settings.OPENAI_API_KEY to empty
    original = client._transport.app.state.settings.OPENAI_API_KEY
    client._transport.app.state.settings.OPENAI_API_KEY = ""
    try:
        payload = {"audio_url": "https://example.com/audio.ogg"}
        response = await client.post(
            "/api/v1/transcription", json=payload, headers=auth_headers
        )
        assert response.status_code == 503
    finally:
        client._transport.app.state.settings.OPENAI_API_KEY = original


@pytest.mark.asyncio
async def test_transcribe_rejects_private_audio_url(client, auth_headers):
    payload = {"audio_url": "http://127.0.0.1/audio.ogg"}
    response = await client.post("/api/v1/transcription", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_transcribe_unauthorized(client):
    """POST /api/v1/transcription without auth returns 401/403."""
    payload = {"audio_url": "https://example.com/audio.ogg"}
    response = await client.post("/api/v1/transcription", json=payload)
    assert response.status_code in (401, 403)
