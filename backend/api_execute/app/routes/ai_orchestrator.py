"""AI Orchestrator route — api_execute builds business context, ai_dialer processes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.dependencies import get_db
from shared.database.session import set_tenant_context
from shared.middleware.rate_limit import require_rate_limit

from app.routes.deps import AiChatActor
from app.schemas.ai_orchestrator import ProcessMessageRequest, ProcessMessageResponse
from app.services.ai_orchestrator import orchestrate_chat

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

    api_execute builds the full business context (prompt + knowledge + products)
    and forwards to ai_dialer for LLM processing.
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
