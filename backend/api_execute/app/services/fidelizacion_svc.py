"""Fidelización service — updates lead stats after a comanda is delivered."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comanda import Comanda, ComandaItem
from app.models.lead import Lead
from app.models.producto import Producto


def compute_estado_cliente(total_pedidos: int) -> str:
    """Determine loyalty tier based on total orders.

    Tiers:
        1       → NUEVO
        2-4     → OCASIONAL
        5-9     → FRECUENTE
        10+     → VIP

    INACTIVO is set by a separate scheduled job, not here.
    """
    if total_pedidos <= 1:
        return "NUEVO"
    if total_pedidos <= 4:
        return "OCASIONAL"
    if total_pedidos <= 9:
        return "FRECUENTE"
    return "VIP"


async def _fetch_plato_favorito(
    db: AsyncSession, tenant_id: UUID, cliente_id: UUID,
) -> str | None:
    """Find the most ordered product name for a lead."""
    fav_query = (
        select(Producto.nombre, func.sum(ComandaItem.cantidad).label("total_qty"))
        .join(ComandaItem, ComandaItem.producto_id == Producto.id)
        .join(Comanda, Comanda.id == ComandaItem.comanda_id)
        .where(
            Comanda.tenant_id == tenant_id,
            Comanda.cliente_id == cliente_id,
            Comanda.estado == "ENTREGADO",
        )
        .group_by(Producto.nombre)
        .order_by(func.sum(ComandaItem.cantidad).desc())
        .limit(1)
    )
    row = (await db.execute(fav_query)).first()
    return row[0] if row else None


async def _compute_frecuencia_dias(
    db: AsyncSession, tenant_id: UUID, cliente_id: UUID, total_pedidos: int,
) -> int | None:
    """Compute avg days between orders for a lead."""
    if total_pedidos < 2:
        return None
    dr = await db.execute(
        select(
            func.min(Comanda.created_at).label("first_at"),
            func.max(Comanda.created_at).label("last_at"),
        ).where(
            Comanda.tenant_id == tenant_id,
            Comanda.cliente_id == cliente_id,
            Comanda.estado == "ENTREGADO",
        )
    )
    row = dr.first()
    if row and row.first_at and row.last_at:
        return max((row.last_at - row.first_at).days // total_pedidos, 1)
    return None


async def update_lead_stats(
    db: AsyncSession, tenant_id: UUID, comanda: Comanda
) -> None:
    """Update lead fidelización stats after a comanda reaches ENTREGADO."""
    if not comanda.cliente_id:
        return

    result = await db.execute(
        select(Lead).where(Lead.id == comanda.cliente_id, Lead.tenant_id == tenant_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        return

    lead.total_pedidos = (lead.total_pedidos or 0) + 1
    comanda_total = sum(float(item.subtotal or 0) for item in comanda.items)
    lead.total_gastado = float(lead.total_gastado or 0) + comanda_total

    plato = await _fetch_plato_favorito(db, tenant_id, comanda.cliente_id)
    if plato:
        lead.plato_favorito = plato

    lead.ultima_visita = date.today()
    freq = await _compute_frecuencia_dias(db, tenant_id, comanda.cliente_id, lead.total_pedidos)
    if freq is not None:
        lead.frecuencia_dias = freq

    lead.estado_cliente = compute_estado_cliente(lead.total_pedidos)
