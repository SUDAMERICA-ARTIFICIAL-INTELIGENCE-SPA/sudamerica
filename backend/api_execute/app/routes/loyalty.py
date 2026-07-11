"""Loyalty routes: outreach triggers and customer retention automation."""

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db

from app.routes.deps import AdminWriter, MetricasReader
from app.services import metrica_svc
from app.services.loyalty_outreach import trigger_loyalty_outreach

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.post("/trigger-outreach")
async def trigger_outreach(
    request: Request,
    max_messages: int = Query(default=10, ge=1, le=50),
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Trigger WhatsApp outreach for at-risk loyal customers.

    Sends personalized messages to VIP/FRECUENTE customers who haven't
    visited in longer than their usual frequency.
    Can be triggered manually or by Cloud Scheduler.
    """
    settings = request.app.state.settings
    tenant_id = current_user["tenant_id"]
    result = await trigger_loyalty_outreach(
        settings, db, tenant_id, max_messages=max_messages,
    )
    return result
