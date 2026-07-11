"""Schemas for the AI orchestrator endpoint."""

from uuid import UUID

from pydantic import BaseModel, Field


class ProcessMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    lead_id: UUID | None = None
    contact_id: UUID | None = None
    session_id: UUID | None = None
    canal: str = "WEB"
    media_url: str | None = None
    media_type: str | None = None


class PollData(BaseModel):
    question: str
    options: list[str]
    selectable_count: int = 1


class ListSection(BaseModel):
    title: str = ""
    rows: list[dict] = Field(default_factory=list)


class ListData(BaseModel):
    title: str
    button_text: str
    sections: list[ListSection] = Field(default_factory=list)


class ProcessMessageResponse(BaseModel):
    response: str
    conversation_id: UUID
    session_id: UUID | None = None
    tokens_used: int
    sub_agente_usado: str | None = None
    confianza: float
    sources: list[str] = Field(default_factory=list)
    comanda_created: bool = False
    media_url: str | None = None
    media_type: str | None = None
    media_file_name: str | None = None
    poll: PollData | None = None
    list_message: ListData | None = None
    audio_base64: str | None = None
