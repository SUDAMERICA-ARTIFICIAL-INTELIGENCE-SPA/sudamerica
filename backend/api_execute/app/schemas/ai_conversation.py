"""Schemas for AI conversation summaries surfaced in the /ia dashboard."""

import math
from datetime import datetime

from pydantic import BaseModel


class AIConversationSummary(BaseModel):
    """Conversation-level aggregate — one row per lead conversation."""

    id: str
    tenant_id: str
    lead_id: str
    canal: str | None = None
    resuelto_sin_humano: bool
    confidence: float
    token_cost: float
    duracion_segundos: float
    created_at: datetime


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class AIConversationsPaginated(BaseModel):
    data: list[AIConversationSummary]
    meta: PaginationMeta
