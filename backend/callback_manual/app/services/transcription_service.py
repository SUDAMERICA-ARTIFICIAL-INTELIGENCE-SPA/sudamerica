"""Audio transcription service using OpenAI Whisper API."""

import asyncio
import ipaddress
import logging
import socket
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".oga": "audio/ogg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
}


@dataclass(slots=True)
class DownloadedAudio:
    filename: str
    content_type: str
    content: bytes


async def transcribe_audio(
    audio_url: str,
    api_key: str,
) -> tuple[str, float]:
    """Download audio from URL and transcribe via Whisper."""
    audio = await _download_audio(audio_url)
    text, duration = await _call_whisper(audio, api_key)
    return text, duration


def _check_content_length(headers: httpx.Headers) -> None:
    """Raise ValueError if Content-Length exceeds limit."""
    content_length = _parse_content_length(headers.get("Content-Length"))
    if content_length is not None and content_length > MAX_AUDIO_SIZE_BYTES:
        raise ValueError("audio file exceeds 25 MB limit")


async def _stream_audio_chunks(response: httpx.Response) -> list[bytes]:
    """Read streamed chunks, enforcing size limit."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_AUDIO_SIZE_BYTES:
            raise ValueError("audio file exceeds 25 MB limit")
    return chunks


async def _download_audio(audio_url: str) -> DownloadedAudio:
    """Download a remote audio file after validating the URL."""
    await _validate_audio_url(audio_url)
    try:
        chunks, filename, content_type = await _fetch_audio_stream(audio_url)
    except ValueError:
        raise
    except httpx.HTTPStatusError as exc:
        logger.warning("Audio download failed with status %s for %s", exc.response.status_code, audio_url)
        raise RuntimeError("unable to download audio file") from exc
    except httpx.HTTPError as exc:
        logger.warning("Audio download failed for %s: %s", audio_url, exc)
        raise RuntimeError("unable to download audio file") from exc
    return DownloadedAudio(filename=filename, content_type=content_type, content=b"".join(chunks))


async def _fetch_audio_stream(audio_url: str) -> tuple[list[bytes], str, str]:
    """Open HTTP stream, validate headers, and read audio chunks."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        async with client.stream("GET", audio_url) as response:
            response.raise_for_status()
            _check_content_length(response.headers)
            filename, content_type = _resolve_audio_metadata(
                audio_url, response.headers.get("Content-Type"),
            )
            chunks = await _stream_audio_chunks(response)
    return chunks, filename, content_type


async def _call_whisper(audio: DownloadedAudio, api_key: str) -> tuple[str, float]:
    """Send audio bytes to OpenAI Whisper API for transcription."""
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (audio.filename, audio.content, audio.content_type)}
    data = {"model": "whisper-1", "response_format": "verbose_json"}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                WHISPER_URL,
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("Whisper rejected audio upload: %s", exc.response.status_code)
        raise RuntimeError("whisper transcription failed") from exc
    except httpx.HTTPError as exc:
        logger.warning("Whisper request failed: %s", exc)
        raise RuntimeError("whisper transcription failed") from exc

    elapsed = time.monotonic() - start
    body = response.json()
    text = body.get("text", "")
    duration = body.get("duration", elapsed)
    return text, float(duration)


async def _validate_audio_url(audio_url: str) -> None:
    parsed = urlparse(audio_url)
    _validate_url_scheme_and_host(parsed)
    host = parsed.hostname.strip()
    await _validate_host_is_public(host)


def _validate_url_scheme_and_host(parsed) -> None:
    """Validate URL scheme, hostname presence, and absence of credentials."""
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("audio_url must use http or https")
    if not parsed.hostname:
        raise ValueError("audio_url must include a valid host")
    if parsed.username or parsed.password:
        raise ValueError("audio_url cannot include credentials")
    if parsed.hostname.strip().lower() == "localhost":
        raise ValueError("audio_url host is not allowed")


async def _validate_host_is_public(host: str) -> None:
    """Ensure the host resolves to only public (global) IP addresses."""
    literal_ip = _parse_ip_address(host)
    if literal_ip is not None:
        if not literal_ip.is_global:
            raise ValueError("audio_url must resolve to a public address")
        return

    addresses = await _resolve_host_addresses(host)
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("audio_url must resolve to a public address")


async def _resolve_host_addresses(host: str) -> set[str]:
    """Resolve a hostname to a set of IP address strings."""
    try:
        resolved_hosts = await asyncio.to_thread(socket.getaddrinfo, host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("audio_url host could not be resolved") from exc
    addresses = {item[4][0] for item in resolved_hosts}
    if not addresses:
        raise ValueError("audio_url host could not be resolved")
    return addresses


def _resolve_audio_metadata(
    audio_url: str,
    content_type_header: str | None,
) -> tuple[str, str]:
    path = PurePosixPath(urlparse(audio_url).path)
    extension = path.suffix.lower()
    filename = path.name or "audio"

    if extension in SUPPORTED_AUDIO_TYPES:
        return filename, SUPPORTED_AUDIO_TYPES[extension]

    content_type = (content_type_header or "").split(";", 1)[0].strip().lower()
    if content_type in SUPPORTED_AUDIO_TYPES.values():
        extension = next(
            (suffix for suffix, media_type in SUPPORTED_AUDIO_TYPES.items() if media_type == content_type),
            ".bin",
        )
        if not path.suffix:
            filename = f"audio{extension}"
        return filename, content_type

    raise ValueError("unsupported audio format")


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        content_length = int(value)
    except ValueError as exc:
        raise ValueError("invalid Content-Length header") from exc
    if content_length < 0:
        raise ValueError("invalid Content-Length header")
    return content_length


def _parse_ip_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None
