"""Schemas for the send-response endpoint."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MediaType = Literal["image", "document", "video", "audio"]


class SendResponseRequest(BaseModel):
    """Payload from callback_manual after human approves/edits a response."""

    revision_id: UUID
    lead_id: UUID | None = None
    respuesta: str | None = Field(default=None, max_length=8000)
    # Media fields (optional — for forwarding media alongside text)
    media_url: str | None = None
    media_type: MediaType | None = None
    file_name: str | None = None
    caption: str | None = None
    mimetype: str | None = None

    @model_validator(mode="after")
    def _require_text_or_media(self):
        has_text = self.respuesta and self.respuesta.strip()
        if not has_text and not self.media_url:
            raise ValueError("Either respuesta or media_url is required")
        return self


class SendResponseResponse(BaseModel):
    """Result of the send-response operation."""

    success: bool
    canal: str | None = None
    detail: str | None = None
