"""Schemas for WhatsApp messaging via Evolution API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MediaType = Literal["image", "document", "video", "audio"]


class WhatsAppIncoming(BaseModel):
    """Payload received from Evolution API webhook."""

    sender: str
    message: str = ""
    media_url: str | None = None
    media_type: MediaType | None = None
    mimetype: str | None = None
    file_name: str | None = None
    instance_name: str
    from_me: bool = False


class WhatsAppOutgoing(BaseModel):
    """Request body to send a WhatsApp message (text or media)."""

    to: str
    message: str | None = None
    tenant_id: UUID
    # Media fields (optional — omit for text-only messages)
    media_url: str | None = None
    media_type: MediaType | None = None
    file_name: str | None = None
    caption: str | None = None
    mimetype: str | None = None

    @model_validator(mode="after")
    def _require_message_or_media(self):
        if not self.message and not self.media_url:
            raise ValueError("Either message or media_url is required")
        return self


class WhatsAppResponse(BaseModel):
    """Response after sending a WhatsApp message."""

    success: bool
    message_id: str | None = None


class InstanceSettingsRequest(BaseModel):
    """Defensive settings for a WhatsApp instance (anti-ban)."""

    reject_call: bool = True
    always_online: bool = True
    read_messages: bool = True


class InstanceSettingsResponse(BaseModel):
    """Confirmation that instance settings were applied."""

    success: bool
    instance_name: str


class WhatsAppReplyRequest(BaseModel):
    """Human agent reply to a WhatsApp prospect (text or media)."""

    lead_id: UUID
    message: str | None = Field(default=None, max_length=4096)
    # Media fields (optional)
    media_url: str | None = None
    media_type: MediaType | None = None
    file_name: str | None = None
    caption: str | None = None
    mimetype: str | None = None

    @model_validator(mode="after")
    def _require_message_or_media(self):
        has_text = self.message and self.message.strip()
        if not has_text and not self.media_url:
            raise ValueError("Either message or media_url is required")
        return self


class WhatsAppReplyResponse(BaseModel):
    """Confirmation that a human reply was sent and persisted."""

    success: bool
    message_id: str | None = None
    lead_id: UUID


class WhatsAppOutboundRequest(BaseModel):
    """Request to send an outbound WhatsApp message to a lead."""

    lead_id: str
    message: str | None = Field(default=None, max_length=4096)
    use_ai: bool = False
    # Media fields (optional)
    media_url: str | None = None
    media_type: MediaType | None = None
    file_name: str | None = None
    caption: str | None = None
    mimetype: str | None = None

    @model_validator(mode="after")
    def _require_message_or_media(self):
        has_text = self.message and self.message.strip()
        if not has_text and not self.media_url:
            raise ValueError("Either message or media_url (or use_ai) is required")
        return self


class WhatsAppHistorySyncRequest(BaseModel):
    """Manual trigger to backfill existing WhatsApp chats into Prospectos."""

    page_size: int = Field(default=200, ge=1, le=500)
    max_chats: int | None = Field(default=None, ge=1, le=1000)
    since: datetime | None = None


class WhatsAppHistorySyncResponse(BaseModel):
    """Summary for a historical WhatsApp sync run."""

    success: bool
    instance_name: str
    chats_scanned: int
    chats_imported: int
    chats_failed: int
    messages_imported: int
    messages_skipped: int


class MediaUploadResponse(BaseModel):
    """Response after uploading a file to GCS."""

    success: bool
    media_url: str
    media_type: MediaType
    file_name: str | None = None
    mimetype: str
