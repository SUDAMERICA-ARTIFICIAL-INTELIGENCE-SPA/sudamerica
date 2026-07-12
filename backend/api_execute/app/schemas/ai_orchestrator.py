"""Schemas for the AI orchestrator endpoint."""

from uuid import UUID

from pydantic import BaseModel, Field


class AgentConfigResponse(BaseModel):
    """Tenant agent flags consumed by canales_service (auto-response + debounce).

    Served by api_execute (owner of ``agente_config``) over ``GET /ai/config``.
    Only the two fields canales_service reads are exposed; defaults match the DB
    column defaults.
    """

    auto_respuesta_whatsapp: bool = True
    debounce_seconds: float = 4.0


class ConversationImportMessage(BaseModel):
    role: str
    content: str
    created_at: str | None = None
    media_url: str | None = None
    media_type: str | None = None


class ConversationImportRequest(BaseModel):
    lead_id: UUID
    canal: str = "WHATSAPP"
    messages: list[ConversationImportMessage] = Field(default_factory=list)


class ConversationImportResponse(BaseModel):
    lead_id: UUID
    imported_count: int = 0
    skipped_count: int = 0


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
