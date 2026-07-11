"""Email sending route."""

import logging
from typing import Annotated

import aiosmtplib
from fastapi import APIRouter, Depends, Request

from app.config import TasksSettings
from app.schemas.email import EmailRequest, EmailResponse
from app.services import email_service
from shared.middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])
CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.post(
    "/email/send",
    response_model=EmailResponse,
)
async def send_email(
    body: EmailRequest,
    request: Request,
    current_user: CurrentUser = None,
) -> EmailResponse:
    """Send an email via SMTP (authenticated)."""
    settings: TasksSettings = request.app.state.settings

    try:
        result = await email_service.send_email(
            to=body.to,
            subject=body.subject,
            body=body.body,
            html=body.html,
            settings=settings,
        )
        return EmailResponse(
            success=result["success"],
            message_id=result.get("message_id"),
        )
    except (aiosmtplib.SMTPException, OSError, ValueError) as exc:
        logger.exception("Failed to send email to %s", body.to, exc_info=exc)
        return EmailResponse(success=False, message_id=None)
