"""Email sending via aiosmtplib with STARTTLS."""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import TasksSettings

logger = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    html: str | None,
    settings: TasksSettings,
) -> dict:
    """Send an email using SMTP with STARTTLS."""
    msg = _build_message(to, subject, body, html, settings)
    message_id = await _deliver(msg, settings)
    logger.info("Email sent to %s, message_id=%s", to, message_id)
    return {"success": True, "message_id": message_id}


def _build_message(
    to: str,
    subject: str,
    body: str,
    html: str | None,
    settings: TasksSettings,
) -> EmailMessage:
    """Construct a MIME email message."""
    msg = EmailMessage()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


async def _deliver(
    msg: EmailMessage,
    settings: TasksSettings,
) -> str:
    """Send the message via aiosmtplib with STARTTLS."""
    response, message_text = await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
    logger.debug("SMTP response: %s %s", response, message_text)
    return msg["Message-ID"] or "unknown"
