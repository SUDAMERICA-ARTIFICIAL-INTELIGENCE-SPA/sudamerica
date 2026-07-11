"""AI conversation summary routes for the /ia dashboard."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

from app.routes.deps import MetricasReader
from app.schemas.ai_conversation import AIConversationsPaginated
from app.services import ai_conversation_svc

router = APIRouter(prefix="/ai-conversations", tags=["ai-conversations"])


@router.get("", response_model=AIConversationsPaginated)
async def list_ai_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    lead_id: str | None = Query(None),
    resuelto_sin_humano: bool | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    current_user: dict = MetricasReader,
    db: AsyncSession = Depends(get_db),
):
    """Paginated AI conversation summaries (grouped by lead)."""
    return await ai_conversation_svc.list_conversations(
        db,
        current_user["tenant_id"],
        page=page,
        page_size=page_size,
        lead_id=lead_id,
        resuelto_sin_humano=resuelto_sin_humano,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
