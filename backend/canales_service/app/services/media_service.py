"""Media service — handles media download from Evolution API and upload to GCS.

Responsibilities:
- Download media from Evolution API (base64 endpoint)
- Upload media to Google Cloud Storage
- Generate signed URLs for media access
- Detect media type from Evolution webhook payloads
"""

import base64
import logging
from typing import Any
from uuid import UUID

from app.config import CanalesSettings
from shared.utils.http_client import HttpClient
from shared.utils.storage import build_media_path, generate_signed_url, upload_bytes

logger = logging.getLogger(__name__)

# Map Evolution API message types to our media categories
_EVOLUTION_MEDIA_TYPES: dict[str, str] = {
    "audioMessage": "audio",
    "imageMessage": "image",
    "videoMessage": "video",
    "documentMessage": "document",
    "stickerMessage": "image",
}

_MIME_TO_EXT: dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/ogg; codecs=opus": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/wav": "wav",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def detect_media_from_payload(message: dict[str, Any]) -> dict[str, Any] | None:
    """Extract media info from an Evolution API webhook message payload.

    Returns dict with keys: media_type, mimetype, file_name, seconds (audio)
    or None if no media detected.
    """
    if not isinstance(message, dict):
        return None

    for msg_key, media_type in _EVOLUTION_MEDIA_TYPES.items():
        media_msg = message.get(msg_key)
        if media_msg is not None:
            logger.info("detect_media: found key=%s type=%s isinstance_dict=%s", msg_key, type(media_msg).__name__, isinstance(media_msg, dict))
        if not isinstance(media_msg, dict):
            continue

        mimetype = media_msg.get("mimetype", "application/octet-stream")
        result: dict[str, Any] = {
            "media_type": media_type,
            "mimetype": mimetype,
            "message_key": msg_key,
        }

        if media_type == "audio":
            result["seconds"] = media_msg.get("seconds", 0)
            result["ptt"] = media_msg.get("ptt", False)

        if media_type == "document":
            result["file_name"] = media_msg.get("fileName") or media_msg.get("title") or "document"

        caption = media_msg.get("caption")
        if caption:
            result["caption"] = caption

        return result

    return None


async def download_media_from_evolution(
    instance_name: str,
    message_id: str,
    remote_jid: str,
    settings: CanalesSettings,
) -> tuple[bytes, str] | None:
    """Download media from Evolution API using getBase64 endpoint.

    Returns (raw_bytes, mimetype) or None if download fails.
    """
    client = HttpClient(base_url=settings.EVOLUTION_API_URL, timeout=30.0)
    headers = {"apikey": settings.EVOLUTION_API_KEY}

    payload = {
        "message": {
            "key": {
                "id": message_id,
                "remoteJid": remote_jid,
            }
        },
        "convertToMp4": False,
    }

    try:
        response = await client.post(
            f"/chat/getBase64FromMediaMessage/{instance_name}",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

        b64_data = body.get("base64", "")
        mimetype = body.get("mimetype", "application/octet-stream")

        if not b64_data:
            logger.warning("Empty base64 response from Evolution API for message %s", message_id)
            return None

        raw_bytes = base64.b64decode(b64_data)
        logger.info("Downloaded %d bytes of media from Evolution API (message=%s)", len(raw_bytes), message_id)
        return raw_bytes, mimetype

    except Exception:
        logger.exception("Failed to download media from Evolution API (message=%s)", message_id)
        return None


async def upload_media_to_gcs(
    data: bytes,
    tenant_id: UUID,
    media_type: str,
    mimetype: str,
    settings: CanalesSettings,
) -> tuple[str, str]:
    """Upload media bytes to GCS. Returns (blob_path, signed_url)."""
    base_mime = mimetype.split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(base_mime, _MIME_TO_EXT.get(mimetype, "bin"))

    blob_path = build_media_path(str(tenant_id), media_type, ext)
    upload_bytes(settings.GCS_BUCKET_NAME, data, blob_path, content_type=mimetype)

    signed_url = generate_signed_url(
        settings.GCS_BUCKET_NAME,
        blob_path,
        expiration_hours=settings.GCS_SIGNED_URL_EXPIRY_HOURS,
    )

    logger.info(
        "Media uploaded to GCS: gs://%s/%s (type=%s, size=%d)",
        settings.GCS_BUCKET_NAME, blob_path, media_type, len(data),
    )
    return blob_path, signed_url


async def send_media_via_evolution(
    to: str,
    media_url: str,
    media_type: str,
    instance_name: str,
    settings: CanalesSettings,
    file_name: str | None = None,
    caption: str | None = None,
    mimetype: str | None = None,
) -> dict:
    """Send media via Evolution API /message/sendMedia endpoint.

    Args:
        to: Phone number (e.g., "56912345678")
        media_url: Public URL of the media file
        media_type: One of "image", "document", "video", "audio"
        instance_name: Evolution API instance name
        settings: Canales settings
        file_name: File name (required for documents)
        caption: Optional caption/description
        mimetype: MIME type hint
    """
    from app.services.whatsapp_service import _enforce_send_rate_limit

    _enforce_send_rate_limit(instance_name)
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    headers = {"apikey": settings.EVOLUTION_API_KEY}

    payload: dict[str, Any] = {
        "number": to,
        "mediatype": media_type,
        "media": media_url,
    }
    if file_name:
        payload["fileName"] = file_name
    if caption:
        payload["caption"] = caption
    if mimetype:
        payload["mimetype"] = mimetype

    response = await client.post(
        f"/message/sendMedia/{instance_name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    logger.info("WhatsApp media sent to %s via %s (type=%s)", to, instance_name, media_type)
    return response.json()
