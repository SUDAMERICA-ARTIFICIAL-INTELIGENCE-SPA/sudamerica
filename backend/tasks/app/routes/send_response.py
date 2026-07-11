"""Route: forward approved/edited AI responses to leads."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import TasksSettings
from app.schemas.send_response import SendResponseRequest, SendResponseResponse
from app.services import send_response_service
from shared.database.dependencies import get_db
from shared.middleware import require_user_or_service
from shared.models.enums import UserRole
from shared.utils.service_access import SEND_RESPONSE_CALLERS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["send-response"])
CurrentActor = Annotated[
    dict,
    Depends(
        require_user_or_service(
            UserRole.ADMIN,
            UserRole.ASESOR,
            UserRole.VIEWER,
            service_scopes=("tasks:send_response",),
            service_callers=SEND_RESPONSE_CALLERS,
        )
    ),
]


@router.post(
    "/send-response",
    response_model=SendResponseResponse,
)
async def send_response(
    body: SendResponseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActor = ...,
) -> SendResponseResponse:
    """Deliver an approved/edited AI response to the lead.

    Called by callback_manual after a human reviewer approves or edits
    the AI-generated response.
    """
    settings: TasksSettings = request.app.state.settings
    tenant_id = current_user["tenant_id"]

    result = await send_response_service.deliver_response(
        session=db,
        tenant_id=tenant_id,
        lead_id=body.lead_id,
        respuesta=body.respuesta,
        revision_id=body.revision_id,
        settings=settings,
        media_url=body.media_url,
        media_type=body.media_type,
        file_name=body.file_name,
        caption=body.caption,
        mimetype=body.mimetype,
    )
    return SendResponseResponse(**result)


@router.post("/retry-failed")
async def retry_failed_deliveries(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentActor = ...,
):
    """Re-attempt delivery for all FAILED revisions in the tenant."""
    settings: TasksSettings = request.app.state.settings
    tenant_id = current_user["tenant_id"]

    result = await send_response_service.retry_failed_deliveries(
        session=db,
        tenant_id=tenant_id,
        settings=settings,
    )
    return result
