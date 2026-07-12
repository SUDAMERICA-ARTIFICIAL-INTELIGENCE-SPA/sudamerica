"""User-facing AI dashboard routes — config, conversations, knowledge.

api_execute owns ``agente_config``, ``ai_conversations`` and ``tenant_knowledge``.
These endpoints serve the web dashboard (config editor, conversation viewer,
training/knowledge) under ``/api/v1/core/ai/*`` — replacing the removed ai_dialer.
The request/response shapes mirror the old AI_dialer so the frontend is unchanged.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.dependencies import get_db
from shared.middleware.auth import require_user_or_service
from shared.models.enums import UserRole
from shared.utils.service_access import AGENT_CONFIG_READERS

from app.config import ApiExecuteSettings
from app.routes.deps import AdminWriter, AnyAuthenticated, get_settings
from app.schemas.agente_config import AgenteConfigResponse, AgenteConfigUpdate
from app.schemas.conversation import PaginatedMessages, PaginatedThreads
from app.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeListResponse,
    KnowledgeResponse,
    KnowledgeUpdate,
    TeachRequest,
    TeachResponse,
    TestRequest,
    TestResponse,
)
from app.services import agente_config_svc, conversation_svc, knowledge_svc

router = APIRouter(tags=["ai-dashboard"])

# GET /ai/config is readable by dashboard users AND by canales_service (which only
# reads auto_respuesta_whatsapp/debounce_seconds from the full object).
_CONFIG_READ_ROLES = (
    UserRole.SUPERADMIN,
    UserRole.ADMIN,
    UserRole.GERENTE,
    UserRole.MESERO,
    UserRole.COCINA,
    UserRole.CAJA,
    UserRole.PERSONAL,
    UserRole.ASESOR,
    UserRole.VIEWER,
)
AgentConfigReader = Depends(
    require_user_or_service(
        *_CONFIG_READ_ROLES,
        service_scopes=("config:read",),
        service_callers=AGENT_CONFIG_READERS,
    )
)


# ─── Config ──────────────────────────────────────────────────────────────────


@router.get("/ai/config", response_model=AgenteConfigResponse)
async def get_agente_config(
    current_actor: dict = AgentConfigReader,
    db: AsyncSession = Depends(get_db),
) -> AgenteConfigResponse:
    """Return the tenant's full agent config, auto-creating a default if absent."""
    data = await agente_config_svc.get_or_create_agente_config(
        db, current_actor["tenant_id"]
    )
    return AgenteConfigResponse(**data)


@router.patch("/ai/config", response_model=AgenteConfigResponse)
async def update_agente_config(
    body: AgenteConfigUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
) -> AgenteConfigResponse:
    """Update the tenant's agent config (only supplied fields)."""
    data = await agente_config_svc.update_agente_config(
        db, current_user["tenant_id"], body.model_dump(exclude_unset=True)
    )
    return AgenteConfigResponse(**data)


# ─── Conversations (viewer) ──────────────────────────────────────────────────


@router.get("/ai/conversations", response_model=PaginatedThreads)
async def list_conversation_threads(
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    canal: str | None = Query(None),
):
    """Conversation threads grouped by lead (newest first)."""
    return await conversation_svc.list_threads(
        db, current_user["tenant_id"], page=page, page_size=page_size, canal=canal
    )


@router.get(
    "/ai/conversations/{lead_id}/messages", response_model=PaginatedMessages
)
async def list_conversation_messages(
    lead_id: UUID,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Messages for one lead, chronological within the page."""
    return await conversation_svc.list_messages(
        db, current_user["tenant_id"], lead_id, page=page, page_size=page_size
    )


# ─── Knowledge / training ────────────────────────────────────────────────────
# NOTE: /ai/knowledge/teach and /ai/knowledge/test are declared BEFORE the
# /ai/knowledge/{knowledge_id} routes so the path param does not swallow them.


@router.post("/ai/knowledge/teach", response_model=TeachResponse, status_code=201)
async def teach_knowledge(
    body: TeachRequest,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(get_settings),
) -> TeachResponse:
    """Persist a training snippet; the title is extracted via the LLM (or derived)."""
    result = await knowledge_svc.teach(db, current_user["tenant_id"], body.content, settings)
    return TeachResponse(**result)


@router.post("/ai/knowledge/test", response_model=TestResponse)
async def test_knowledge(
    body: TestRequest,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(get_settings),
) -> TestResponse:
    """Generate a trial answer from the tenant's knowledge (nothing persisted)."""
    result = await knowledge_svc.test_message(
        db, current_user["tenant_id"], body.message, settings
    )
    return TestResponse(**result)


@router.get("/ai/knowledge", response_model=KnowledgeListResponse)
async def list_knowledge(
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    type: str | None = Query(None),
):
    """Paginated list of the tenant's active knowledge entries."""
    entries, total = await knowledge_svc.list_knowledge(
        db, current_user["tenant_id"], type_filter=type, page=page, page_size=page_size
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": entries,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }


@router.get("/ai/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: UUID,
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Return a single knowledge entry."""
    entry = await knowledge_svc.get_knowledge(db, current_user["tenant_id"], knowledge_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.post("/ai/knowledge", response_model=KnowledgeResponse, status_code=201)
async def create_knowledge(
    body: KnowledgeCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a knowledge entry."""
    return await knowledge_svc.create_knowledge(
        db,
        current_user["tenant_id"],
        type_=body.type,
        title=body.title,
        content=body.content,
        priority=body.priority,
    )


@router.patch("/ai/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    knowledge_id: UUID,
    body: KnowledgeUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge entry (only supplied fields)."""
    entry = await knowledge_svc.update_knowledge(
        db, current_user["tenant_id"], knowledge_id, body.model_dump(exclude_unset=True)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.delete("/ai/knowledge/{knowledge_id}", status_code=204)
async def delete_knowledge(
    knowledge_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a knowledge entry (activo=false)."""
    deleted = await knowledge_svc.delete_knowledge(
        db, current_user["tenant_id"], knowledge_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return Response(status_code=204)
