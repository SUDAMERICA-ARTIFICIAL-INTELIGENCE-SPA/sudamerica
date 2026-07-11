"""WhatsApp QR onboarding via Evolution API."""

import asyncio
import base64
import logging
from io import BytesIO

import qrcode

from app.config import CanalesSettings
from shared.utils.http_client import HttpClient

logger = logging.getLogger(__name__)
WEBHOOK_EVENTS = ["QRCODE_UPDATED", "MESSAGES_UPSERT", "CONNECTION_UPDATE"]


async def create_instance(
    instance_name: str,
    settings: CanalesSettings,
    phone_number: str | None = None,
) -> dict:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    response = await client.post(
        "/instance/create",
        headers=_headers(settings),
        json=_create_payload(instance_name, phone_number, settings),
    )
    response.raise_for_status()
    await _set_webhook(client, instance_name, settings)
    logger.info("WhatsApp instance created: %s", instance_name)
    return response.json()


async def set_instance_proxy(
    instance_name: str,
    proxy_host: str,
    proxy_port: str,
    proxy_protocol: str,
    settings: CanalesSettings,
    proxy_username: str | None = None,
    proxy_password: str | None = None,
) -> dict:
    """Set proxy on an existing Baileys instance."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    payload = {
        "proxyHost": proxy_host,
        "proxyPort": proxy_port,
        "proxyProtocol": proxy_protocol,
    }
    if proxy_username:
        payload["proxyUsername"] = proxy_username
        payload["proxyPassword"] = proxy_password or ""
    response = await client.post(
        f"/proxy/set/{instance_name}",
        headers=_headers(settings),
        json=payload,
    )
    response.raise_for_status()
    logger.info("Proxy set for instance %s: %s:%s", instance_name, proxy_host, proxy_port)
    return response.json()


async def create_cloud_api_instance(
    instance_name: str,
    meta_token: str,
    meta_number_id: str,
    meta_business_id: str,
    settings: CanalesSettings,
) -> dict:
    """Create a WhatsApp Business Cloud API instance (no QR scan required)."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    payload = {
        "instanceName": instance_name,
        "token": meta_token,
        "number": meta_number_id,
        "businessId": meta_business_id,
        "qrcode": False,
        "integration": "WHATSAPP-BUSINESS",
    }
    response = await client.post(
        "/instance/create",
        headers=_headers(settings),
        json=payload,
    )
    response.raise_for_status()
    await _set_webhook(client, instance_name, settings)
    logger.info("WhatsApp Cloud API instance created: %s", instance_name)
    return response.json()


async def ensure_webhook(instance_name: str, settings: CanalesSettings) -> None:
    """Re-apply the webhook configuration for an existing instance."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    await _set_webhook(client, instance_name, settings)
    logger.info("WhatsApp webhook refreshed for instance: %s", instance_name)


async def get_qr_code(
    instance_name: str,
    settings: CanalesSettings,
    phone_number: str | None = None,
) -> dict:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    response = await client.get(
        f"/instance/connect/{instance_name}",
        headers=_headers(settings),
        params=_connect_params(phone_number),
    )
    response.raise_for_status()
    logger.info("QR code retrieved for instance: %s", instance_name)
    return _normalize_connect_response(response.json())


async def get_qr_code_with_retry(
    instance_name: str,
    settings: CanalesSettings,
    phone_number: str | None = None,
    max_retries: int = 10,
    delay: float = 2.0,
) -> dict:
    for attempt in range(max_retries):
        data = await get_qr_code(instance_name, settings, phone_number)
        if data.get("base64", ""):
            return data
        if attempt == max_retries - 1:
            break
        logger.debug("QR not ready for %s (%d/%d)", instance_name, attempt + 1, max_retries)
        await asyncio.sleep(delay)
    raise TimeoutError(f"QR code not available after {max_retries} retries for {instance_name}")


async def get_instance_status(instance_name: str, settings: CanalesSettings) -> dict:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    response = await client.get(
        f"/instance/connectionState/{instance_name}",
        headers=_headers(settings),
    )
    response.raise_for_status()
    return response.json()


async def logout_instance(instance_name: str, settings: CanalesSettings) -> dict:
    """Logout and delete a WhatsApp instance from Evolution API."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    response = await client.delete(
        f"/instance/logout/{instance_name}",
        headers=_headers(settings),
    )
    response.raise_for_status()
    logger.info("WhatsApp instance logged out: %s", instance_name)
    return response.json()


async def delete_instance(instance_name: str, settings: CanalesSettings) -> dict:
    """Delete a WhatsApp instance from Evolution API."""
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    response = await client.delete(
        f"/instance/delete/{instance_name}",
        headers=_headers(settings),
    )
    response.raise_for_status()
    logger.info("WhatsApp instance deleted: %s", instance_name)
    return response.json()


async def configure_instance_settings(
    instance_name: str,
    reject_call: bool,
    always_online: bool,
    read_messages: bool,
    settings: CanalesSettings,
) -> dict:
    client = HttpClient(base_url=settings.EVOLUTION_API_URL)
    payload = {
        "rejectCall": reject_call,
        "msgCall": "Llamada no disponible" if reject_call else "",
        "groupsIgnore": True,
        "alwaysOnline": always_online,
        "readMessages": read_messages,
        "readStatus": True,
        "syncFullHistory": False,
    }
    response = await client.post(
        f"/settings/set/{instance_name}",
        headers=_headers(settings),
        json=payload,
    )
    response.raise_for_status()
    logger.info("Instance settings applied for %s", instance_name)
    return response.json()


def _headers(settings: CanalesSettings) -> dict[str, str]:
    return {"apikey": settings.EVOLUTION_API_KEY}


def _create_payload(
    instance_name: str,
    phone_number: str | None,
    settings: CanalesSettings | None = None,
) -> dict[str, str | bool]:
    payload: dict[str, str | bool] = {
        "instanceName": instance_name,
        "integration": "WHATSAPP-BAILEYS",
        "qrcode": True,
    }
    normalized_number = _normalize_phone(phone_number)
    if normalized_number:
        payload["number"] = normalized_number
    if settings and settings.WA_PROXY_HOST:
        payload["proxyHost"] = settings.WA_PROXY_HOST
        payload["proxyPort"] = settings.WA_PROXY_PORT
        payload["proxyProtocol"] = settings.WA_PROXY_PROTOCOL
        if settings.WA_PROXY_USERNAME:
            payload["proxyUsername"] = settings.WA_PROXY_USERNAME
            payload["proxyPassword"] = settings.WA_PROXY_PASSWORD
    return payload


def _connect_params(phone_number: str | None) -> dict[str, str] | None:
    normalized_number = _normalize_phone(phone_number)
    if not normalized_number:
        return None
    return {"number": normalized_number}


def _normalize_connect_response(data: dict) -> dict:
    normalized_base64 = _normalize_base64(data.get("base64", ""))
    if normalized_base64:
        return {**data, "base64": normalized_base64}
    code = data.get("code")
    if not code:
        return data
    return {**data, "base64": _render_qr_base64(code)}


def _render_qr_base64(code: str) -> str:
    image = qrcode.make(code)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _normalize_base64(value: str) -> str:
    if not value:
        return ""
    if not value.startswith("data:"):
        return value
    _, _, payload = value.partition(",")
    return payload


async def _set_webhook(
    client: HttpClient,
    instance_name: str,
    settings: CanalesSettings,
) -> None:
    if not settings.EVOLUTION_WEBHOOK_URL:
        return
    if not settings.WEBHOOK_TOKEN.strip():
        raise RuntimeError("WEBHOOK_TOKEN is required to configure the Evolution webhook")
    response = await client.post(
        f"/webhook/set/{instance_name}",
        headers=_headers(settings),
        json=_webhook_payload(settings),
    )
    response.raise_for_status()


def _webhook_payload(settings: CanalesSettings) -> dict[str, dict[str, bool | str | list[str]]]:
    if not settings.WEBHOOK_TOKEN.strip():
        raise RuntimeError("WEBHOOK_TOKEN is required to build the Evolution webhook URL")
    return {
        "webhook": {
            "enabled": True,
            "url": settings.EVOLUTION_WEBHOOK_URL,
            "webhookByEvents": False,
            "webhookBase64": True,
            "events": WEBHOOK_EVENTS,
            "headers": {"apikey": settings.WEBHOOK_TOKEN},
        }
    }


def _normalize_phone(phone_number: str | None) -> str | None:
    if not phone_number:
        return None
    digits = "".join(char for char in phone_number if char.isdigit())
    return digits or None
