"""Schemas for email sending."""

from pydantic import BaseModel


class EmailRequest(BaseModel):
    """Request body to send an email."""

    to: str
    subject: str
    body: str
    html: str | None = None


class EmailResponse(BaseModel):
    """Response after sending an email."""

    success: bool
    message_id: str | None = None
