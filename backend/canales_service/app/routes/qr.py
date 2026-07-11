"""QR routes for WhatsApp onboarding."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.qr import (
    CloudAPIRegisterRequest,
    CloudAPIResponse,
    ProxyConfigRequest,
    ProxyConfigResponse,
    QRGenerateRequest,
    QRResponse,
)
from app.services import instance_service, qr_service, whatsapp_service
from shared.database.dependencies import get_db
from shared.database.session import set_tenant_context
from shared.middleware import get_current_user, require_role
from shared.models.enums import UserRole

logger = logging.getLogger(__name__)
CONNECTED_PENDING_SYNC = "CONNECTED_PENDING"
CONNECTED_SYNCED = "CONNECTED_SYNCED"
RECENT_SYNC_LOOKBACK = timedelta(days=2)
RECENT_SYNC_COOLDOWN = timedelta(hours=6)
RECENT_SYNC_MAX_CHATS = 150
RECENT_SYNC_PAGE_SIZE = 100

router = APIRouter(tags=["qr"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_role(UserRole.ADMIN, UserRole.SUPERADMIN))]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/qr/{tenant_id}", response_model=QRResponse)
async def generate_qr(
    tenant_id: UUID,
    request: Request,
    body: QRGenerateRequest | None = None,
    current_user: AdminUser = None,
    db: DbSession = None,
) -> QRResponse:
    """Create or reconnect a WhatsApp instance and return its QR code."""
    _ensure_tenant_access(tenant_id, current_user)
    instance_name = _instance_name(tenant_id)
    settings = request.app.state.settings
    phone_number = body.phone_number if body else None

    connected = await _get_connected_response(
        db,
        tenant_id,
        instance_name,
        phone_number,
        settings,
        request,
    )
    if connected is not None:
        return connected

    evo_token = await _create_instance(instance_name, settings, phone_number)
    await _sync_instance_record(db, tenant_id, instance_name, phone_number, evo_token)
    return await _build_qr_response(db, instance_name, settings, phone_number)


async def _handle_open_state(
    request: Request, tenant_id: UUID, instance_name: str, settings,
) -> None:
    """Persist open state and queue sync. Falls back to best-effort sync on error."""
    try:
        async with _tenant_db_session(request, tenant_id) as db:
            await _mark_connected_and_queue_sync(
                db, tenant_id, instance_name, None, settings, request,
            )
    except (SQLAlchemyError, RuntimeError, ValueError):
        logger.exception(
            "Could not persist WhatsApp open state for tenant %s; running best-effort sync",
            tenant_id,
        )
        _schedule_history_sync(
            request.app.state.session_factory, instance_name, tenant_id, settings,
        )


@router.get("/qr/{tenant_id}/status", response_model=QRResponse)
async def get_qr_status(
    tenant_id: UUID,
    request: Request,
    current_user: CurrentUser = None,
) -> QRResponse:
    """Return the current WhatsApp connection status for a tenant."""
    _ensure_tenant_access(tenant_id, current_user)
    instance_name = _instance_name(tenant_id)
    settings = request.app.state.settings

    try:
        state = await _fetch_instance_state(instance_name, settings)
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.warning("Evolution API unavailable for tenant %s", tenant_id)
        return QRResponse(qr_code="", instance_name=instance_name, status="disconnected")

    if state == "open":
        await _handle_open_state(request, tenant_id, instance_name, settings)
    return QRResponse(qr_code="", instance_name=instance_name, status=state)


@router.delete("/qr/{tenant_id}")
async def disconnect_whatsapp(
    tenant_id: UUID,
    request: Request,
    current_user: AdminUser = None,
    db: DbSession = None,
) -> dict:
    """Logout and disconnect the WhatsApp instance for a tenant."""
    _ensure_tenant_access(tenant_id, current_user)
    instance_name = _instance_name(tenant_id)
    settings = request.app.state.settings

    # 1. Logout from Evolution API (best-effort)
    try:
        await qr_service.logout_instance(instance_name, settings)
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Evolution logout failed for %s (may already be disconnected)", instance_name)

    # 2. Delete from Evolution API (best-effort)
    try:
        await qr_service.delete_instance(instance_name, settings)
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Evolution delete failed for %s (may not exist)", instance_name)

    # 3. Deactivate in DB
    await instance_service.deactivate_instance(db, instance_name)

    return {"status": "disconnected", "instance_name": instance_name}


@router.post("/proxy/{tenant_id}", response_model=ProxyConfigResponse)
async def set_instance_proxy(
    tenant_id: UUID,
    body: ProxyConfigRequest,
    request: Request,
    current_user: AdminUser = None,
    db: DbSession = None,
) -> ProxyConfigResponse:
    """Set proxy on a WhatsApp Baileys instance to avoid IP blocking."""
    _ensure_tenant_access(tenant_id, current_user)
    instance_name = _instance_name(tenant_id)
    settings = request.app.state.settings

    try:
        await qr_service.set_instance_proxy(
            instance_name=instance_name,
            proxy_host=body.proxy_host,
            proxy_port=body.proxy_port,
            proxy_protocol=body.proxy_protocol,
            settings=settings,
            proxy_username=body.proxy_username,
            proxy_password=body.proxy_password,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        logger.error("Failed to set proxy for %s: %s", instance_name, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to configure proxy on WhatsApp instance",
        ) from exc

    return ProxyConfigResponse(
        instance_name=instance_name,
        proxy_host=body.proxy_host,
        proxy_port=body.proxy_port,
        proxy_protocol=body.proxy_protocol,
        status="proxy_configured",
    )


@router.post("/cloud-api/{tenant_id}", response_model=CloudAPIResponse)
async def register_cloud_api(
    tenant_id: UUID,
    body: CloudAPIRegisterRequest,
    request: Request,
    current_user: AdminUser = None,
    db: DbSession = None,
) -> CloudAPIResponse:
    """Register a WhatsApp Business Cloud API instance (no QR scan needed).

    Requires Meta Business Manager credentials: permanent token, number ID, business ID.
    """
    _ensure_tenant_access(tenant_id, current_user)
    instance_name = _instance_name(tenant_id)
    settings = request.app.state.settings

    # Deactivate any existing Baileys instance for this tenant
    existing = await instance_service.get_instance_for_tenant(db, tenant_id)
    if existing is not None:
        await instance_service.deactivate_instance(db, existing.instance_name)

    try:
        result = await qr_service.create_cloud_api_instance(
            instance_name=instance_name,
            meta_token=body.meta_token,
            meta_number_id=body.meta_number_id,
            meta_business_id=body.meta_business_id,
            settings=settings,
        )
    except httpx.HTTPStatusError as exc:
        if _is_existing_instance_error(exc):
            logger.info("Cloud API instance %s already exists, re-registering", instance_name)
            try:
                await qr_service.delete_instance(instance_name, settings)
            except (httpx.HTTPError, RuntimeError):
                pass
            result = await qr_service.create_cloud_api_instance(
                instance_name=instance_name,
                meta_token=body.meta_token,
                meta_number_id=body.meta_number_id,
                meta_business_id=body.meta_business_id,
                settings=settings,
            )
        else:
            raise

    evo_token = _extract_instance_token(result)
    await _register_cloud_api_instance(
        db, tenant_id, instance_name, body, evo_token,
    )

    return CloudAPIResponse(
        instance_name=instance_name,
        status="CONNECTED",
        integration="WHATSAPP-BUSINESS",
        phone_number=body.phone_number,
    )


async def _register_cloud_api_instance(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    body: CloudAPIRegisterRequest,
    evo_token: str | None,
) -> None:
    """Register a Cloud API instance in the DB."""
    from app.models.evolution_instance import EvolutionInstance

    instance = EvolutionInstance(
        tenant_id=tenant_id,
        instance_name=instance_name,
        status="CONNECTED",
        phone_number=body.phone_number,
        evo_token=evo_token,
        integration="WHATSAPP-BUSINESS",
        meta_business_id=body.meta_business_id,
        meta_number_id=body.meta_number_id,
    )
    db.add(instance)
    await db.flush()


def _ensure_tenant_access(tenant_id: UUID, current_user: dict) -> None:
    if tenant_id == current_user.get("tenant_id"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cannot manage instances for another tenant",
    )


def _instance_name(tenant_id: UUID) -> str:
    return f"tenant-{tenant_id}"


async def _get_connected_response(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    phone_number: str | None,
    settings,
    request: Request,
) -> QRResponse | None:
    try:
        state = await _fetch_instance_state(instance_name, settings)
    except (httpx.HTTPError, RuntimeError, ValueError):
        return None
    if state != "open":
        return None

    await _mark_connected_and_queue_sync(
        db,
        tenant_id,
        instance_name,
        phone_number,
        settings,
        request,
    )
    return QRResponse(qr_code="", instance_name=instance_name, status="open")


async def _fetch_instance_state(instance_name: str, settings) -> str:
    status_data = await qr_service.get_instance_status(instance_name, settings)
    instance_info = status_data.get("instance", status_data)
    return instance_info.get("state", "unknown")


async def _ensure_instance_record(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    phone_number: str | None,
) -> None:
    existing = await instance_service.lookup_by_instance_name(db, instance_name)
    if existing is not None:
        return
    await instance_service.register_instance(
        db,
        tenant_id,
        instance_name,
        phone_number=phone_number,
    )


@asynccontextmanager
async def _tenant_db_session(request: Request, tenant_id: UUID):
    session_factory = request.app.state.session_factory
    async with session_factory() as db:
        await set_tenant_context(db, str(tenant_id))
        try:
            yield db
            await db.commit()
        except BaseException:
            await db.rollback()
            raise


async def _mark_connected_and_queue_sync(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    phone_number: str | None,
    settings,
    request: Request,
) -> None:
    existing = await instance_service.lookup_by_instance_name(db, instance_name)
    previous_status = existing.status if existing is not None else None
    previous_updated_at = existing.updated_at if existing is not None else None

    await _ensure_instance_record(db, tenant_id, instance_name, phone_number)
    await _refresh_instance_webhook(instance_name, settings)

    if previous_status == CONNECTED_PENDING_SYNC:
        return

    if previous_status == CONNECTED_SYNCED:
        if _should_refresh_recent_history(previous_updated_at):
            await instance_service.update_status(
                db,
                instance_name,
                CONNECTED_PENDING_SYNC,
                phone_number=phone_number,
            )
            _schedule_history_sync(
                request.app.state.session_factory,
                instance_name,
                tenant_id,
                settings,
                page_size=RECENT_SYNC_PAGE_SIZE,
                max_chats=RECENT_SYNC_MAX_CHATS,
                since=_recent_sync_since(),
            )
        return

    await instance_service.update_status(
        db,
        instance_name,
        CONNECTED_PENDING_SYNC,
        phone_number=phone_number,
    )
    _schedule_history_sync(
        request.app.state.session_factory,
        instance_name,
        tenant_id,
        settings,
    )


async def _run_history_sync(
    session_factory,
    instance_name: str,
    tenant_id: UUID,
    settings,
    page_size: int = 200,
    max_chats: int | None = None,
    since: datetime | None = None,
) -> None:
    final_status = CONNECTED_SYNCED
    try:
        result = await whatsapp_service.sync_historical_conversations(
            instance_name=instance_name,
            tenant_id=tenant_id,
            settings=settings,
            page_size=page_size,
            max_chats=max_chats,
            since=since,
        )
        if result["chats_failed"] > 0:
            final_status = "CONNECTED"
        logger.info(
            "Historical WhatsApp sync completed for %s: chats=%s imported=%s skipped=%s failed=%s",
            instance_name,
            result["chats_scanned"],
            result["messages_imported"],
            result["messages_skipped"],
            result["chats_failed"],
        )
    except (httpx.HTTPError, RuntimeError, ValueError, SQLAlchemyError):
        final_status = "CONNECTED"
        logger.exception("Historical WhatsApp sync failed for %s", instance_name)

    try:
        async with session_factory() as db:
            await set_tenant_context(db, str(tenant_id))
            await instance_service.update_status(db, instance_name, final_status)
            await db.commit()
    except SQLAlchemyError:
        logger.exception("Could not persist historical sync status for %s", instance_name)


def _schedule_history_sync(
    session_factory,
    instance_name: str,
    tenant_id: UUID,
    settings,
    page_size: int = 200,
    max_chats: int | None = None,
    since: datetime | None = None,
) -> asyncio.Task:
    return asyncio.create_task(
        _run_history_sync(
            session_factory,
            instance_name,
            tenant_id,
            settings,
            page_size=page_size,
            max_chats=max_chats,
            since=since,
        )
    )


async def _create_instance(
    instance_name: str,
    settings,
    phone_number: str | None,
) -> str | None:
    try:
        result = await qr_service.create_instance(instance_name, settings, phone_number)
    except httpx.HTTPStatusError as exc:
        if _is_existing_instance_error(exc):
            logger.debug("Instance %s already exists", instance_name)
            return None
        raise
    except httpx.HTTPError:
        raise
    except RuntimeError:
        raise
    return _extract_instance_token(result)


async def _sync_instance_record(
    db: AsyncSession,
    tenant_id: UUID,
    instance_name: str,
    phone_number: str | None,
    evo_token: str | None,
) -> None:
    existing = await instance_service.lookup_by_instance_name(db, instance_name)
    if existing is None:
        await instance_service.register_instance(
            db,
            tenant_id,
            instance_name,
            phone_number=phone_number,
            evo_token=evo_token,
        )
        return
    if phone_number and existing.phone_number != phone_number:
        await instance_service.update_status(
            db,
            instance_name,
            existing.status,
            phone_number=phone_number,
        )


async def _build_qr_response(
    db: AsyncSession,
    instance_name: str,
    settings,
    phone_number: str | None,
) -> QRResponse:
    try:
        await _refresh_instance_webhook(instance_name, settings)
        qr_data = await qr_service.get_qr_code_with_retry(
            instance_name,
            settings,
            phone_number,
        )
        return await _pending_qr_response(db, instance_name, qr_data)
    except TimeoutError:
        logger.warning("QR retry exhausted for %s", instance_name)
        return QRResponse(qr_code="", instance_name=instance_name, status="timeout")
    except (httpx.HTTPError, RuntimeError, ValueError, SQLAlchemyError):
        logger.warning("Could not get QR for %s", instance_name)
        await instance_service.update_status(db, instance_name, "CONNECTED")
        return QRResponse(qr_code="", instance_name=instance_name, status="open")


async def _pending_qr_response(
    db: AsyncSession,
    instance_name: str,
    qr_data: dict,
) -> QRResponse:
    await instance_service.update_status(db, instance_name, "CONNECTING")
    base64_qr = qr_data.get("base64", "")
    qr_code = f"data:image/png;base64,{base64_qr}" if base64_qr else ""
    return QRResponse(qr_code=qr_code, instance_name=instance_name, status="pending")

def _extract_instance_token(result: dict) -> str | None:
    hash_data = result.get("hash")
    if isinstance(hash_data, str):
        return hash_data
    if isinstance(hash_data, dict):
        return hash_data.get("apikey")
    return result.get("instance", {}).get("hash")


async def _refresh_instance_webhook(instance_name: str, settings) -> None:
    try:
        await qr_service.ensure_webhook(instance_name, settings)
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Could not refresh WhatsApp webhook for %s", instance_name)


def _is_existing_instance_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response.status_code == status.HTTP_409_CONFLICT:
        return True
    # Evolution API returns 403 when the instance already exists
    if response.status_code == status.HTTP_403_FORBIDDEN:
        return True
    if response.status_code != status.HTTP_400_BAD_REQUEST:
        return False
    return "exist" in response.text.lower()


def _recent_sync_since() -> datetime:
    return datetime.now(UTC) - RECENT_SYNC_LOOKBACK


def _should_refresh_recent_history(last_sync_at: datetime | None) -> bool:
    if last_sync_at is None:
        return True

    normalized = last_sync_at
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=UTC)

    return normalized <= datetime.now(UTC) - RECENT_SYNC_COOLDOWN
