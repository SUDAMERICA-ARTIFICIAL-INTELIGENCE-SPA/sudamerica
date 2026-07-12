"""Schemas for the dashboard knowledge base + training endpoints.

Mirror of the old AI_dialer knowledge/training shapes so the dashboard hook
(``useTraining``) keeps its exact types. api_execute owns ``tenant_knowledge`` and
serves these over ``GET/POST/PATCH/DELETE /api/v1/core/ai/knowledge*``.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0)


class KnowledgeUpdate(BaseModel):
    type: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None
    priority: int | None = Field(default=None, ge=0)


class KnowledgeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    title: str
    content: str
    priority: int
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeListResponse(BaseModel):
    data: list[KnowledgeResponse]
    meta: dict


class TeachRequest(BaseModel):
    content: str = Field(..., min_length=10)


class TeachResponse(BaseModel):
    id: str  # UUID of created knowledge entry
    title: str
    content: str
    type: str


class TestRequest(BaseModel):
    message: str = Field(..., min_length=1)


class TestResponse(BaseModel):
    response: str
    confidence: float
    sub_agent: str
