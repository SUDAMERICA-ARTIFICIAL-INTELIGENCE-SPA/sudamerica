"""AI Orchestrator route — api_execute builds business context and generates
replies via open_agent. Also owns the tenant agent config and conversation
history endpoints that canales_service reaches on api_execute."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.dependencies import get_db
from shared.database.session import set_tenant_context
from shared.middleware.auth import require_service
from shared.middleware.rate_limit import require_rate_limit
from shared.utils.service_access import AGENT_CONFIG_READERS, CONVERSATION_IMPORTERS

from app.routes.deps import AiChatActor
from app.schemas.ai_orchestrator import (
    AgentConfigResponse,
    ConversationImportRequest,
    ConversationImportResponse,
    ProcessMessageRequest,
    ProcessMessageResponse,
)
from app.services.ai_orchestrator import (
    import_conversation_messages,
    load_agent_flags,
    orchestrate_chat,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-orchestrator"])


@router.post("/ai/process-message", response_model=ProcessMessageResponse)
async def process_message(
    body: ProcessMessageRequest,
    request: Request,
    current_actor: dict = AiChatActor,
    db: AsyncSession = Depends(get_db),
    _rl=require_rate_limit(max_requests=30, window_seconds=60),
) -> ProcessMessageResponse:
    """Process a message through the AI orchestrator.

    api_execute builds the full business context (prompt + knowledge + products),
    generates the reply via open_agent, and persists the conversation.
    """
    tenant_id = current_actor["tenant_id"]
    settings = request.app.state.settings

    await set_tenant_context(db, str(tenant_id))

    try:
        result = await orchestrate_chat(
            session=db,
            tenant_id=tenant_id,
            message=body.message,
            lead_id=body.lead_id,
            canal=body.canal,
            settings=settings,
            contact_id=body.contact_id,
            session_id=body.session_id,
            media_url=body.media_url,
            media_type=body.media_type,
        )
    except Exception:
        logger.exception("AI orchestration failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="AI processing failed")

    return ProcessMessageResponse(**result)


@router.get("/ai/config", response_model=AgentConfigResponse)
async def get_agent_config(
    current_service: dict = Depends(
        require_service("config:read", callers=AGENT_CONFIG_READERS)
    ),
    db: AsyncSession = Depends(get_db),
) -> AgentConfigResponse:
    """Return the tenant's auto-response + debounce flags for canales_service.

    api_execute owns ``agente_config`` and serves these flags directly over
    ``GET /ai/config``; canales_service reads them before auto-replying.
    """
    tenant_id = current_service["tenant_id"]
    await set_tenant_context(db, str(tenant_id))
    flags = await load_agent_flags(db, tenant_id)
    return AgentConfigResponse(**flags)


@router.post("/ai/conversations/import", response_model=ConversationImportResponse)
async def import_conversations(
    body: ConversationImportRequest,
    current_service: dict = Depends(
        require_service("conversations:import", callers=CONVERSATION_IMPORTERS)
    ),
    db: AsyncSession = Depends(get_db),
) -> ConversationImportResponse:
    """Persist historical customer messages for a lead (idempotent).

    api_execute owns ``ai_conversations`` and exposes this
    ``POST /ai/conversations/import`` endpoint for canales_service to store human
    replies, outbound messages and bulk-synced WhatsApp history.
    """
    tenant_id = current_service["tenant_id"]
    await set_tenant_context(db, str(tenant_id))
    result = await import_conversation_messages(
        db, tenant_id, body.lead_id, body.canal, body.messages,
    )
    return ConversationImportResponse(**result)
