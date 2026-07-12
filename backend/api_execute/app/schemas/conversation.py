"""Schemas for the dashboard conversation viewer (threads + messages).

Mirror of the old AI_dialer conversation shapes so the dashboard hooks
(``useConversationThreads`` / ``useConversationMessages``) keep their exact types.
Served by api_execute (owner of ``ai_conversations``) over
``GET /api/v1/core/ai/conversations`` and ``.../{lead_id}/messages``.
"""

from pydantic import BaseModel


class ConversationThreadOut(BaseModel):
    """Summary of a single conversation thread (grouped by lead_id)."""

    lead_id: str
    lead_name: str | None = None
    session_id: str | None = None
    last_message: str
    last_role: str
    last_canal: str | None = None
    message_count: int
    last_message_at: str


class ConversationMessageOut(BaseModel):
    """A single message within a conversation thread."""

    id: str
    role: str
    content: str
    canal: str | None = None
    tokens_used: int | None = None
    modelo: str | None = None
    session_id: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    created_at: str


class PaginationMeta(BaseModel):
    """Standard pagination metadata."""

    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedThreads(BaseModel):
    data: list[ConversationThreadOut]
    meta: PaginationMeta


class PaginatedMessages(BaseModel):
    data: list[ConversationMessageOut]
    meta: PaginationMeta
