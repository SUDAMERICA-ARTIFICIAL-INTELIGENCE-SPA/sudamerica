"""Suministro (insumo genérico) + Receta (BOM) service layer."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suministro import Receta, Suministro
from shared.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


# ── Suministro CRUD ──

async def list_suministros(
    db: AsyncSession, tenant_id: uuid.UUID, *, page: int = 1, page_size: int = 50
) -> tuple[list[Suministro], int]:
    total = (await db.execute(
        select(func.count(Suministro.id)).where(
            Suministro.tenant_id == tenant_id, Suministro.activo.is_(True)
        )
    )).scalar() or 0
    rows = (await db.execute(
        select(Suministro)
        .where(Suministro.tenant_id == tenant_id, Suministro.activo.is_(True))
        .order_by(Suministro.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()
    return list(rows), total


async def create_suministro(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Suministro:
    suministro = Suministro(tenant_id=tenant_id, **data)
    db.add(suministro)
    await db.flush()
    return suministro


async def update_suministro(
    db: AsyncSession, tenant_id: uuid.UUID, suministro_id: uuid.UUID, data: dict
) -> Suministro:
    row = (await db.execute(
        select(Suministro).where(
            Suministro.id == suministro_id,
            Suministro.tenant_id == tenant_id,
            Suministro.activo.is_(True),
        )
    )).scalar_one_or_none()
    if not row:
        raise NotFoundError("Suministro", str(suministro_id))
    for k, v in data.items():
        if v is not None and hasattr(row, k):
            setattr(row, k, v)
    await db.flush()
    return row


async def delete_suministro(
    db: AsyncSession, tenant_id: uuid.UUID, suministro_id: uuid.UUID
) -> Suministro:
    row = (await db.execute(
        select(Suministro).where(
            Suministro.id == suministro_id, Suministro.tenant_id == tenant_id
        )
    )).scalar_one_or_none()
    if not row:
        raise NotFoundError("Suministro", str(suministro_id))
    row.activo = False
    await db.flush()
    return row


# ── Receta CRUD ──

async def list_recetas(
    db: AsyncSession, tenant_id: uuid.UUID, producto_id: uuid.UUID | None = None
) -> list[dict]:
    query = (
        select(Receta)
        .where(Receta.tenant_id == tenant_id, Receta.activo.is_(True))
    )
    if producto_id:
        query = query.where(Receta.producto_id == producto_id)

    rows = (await db.execute(query.order_by(Receta.created_at))).scalars().all()

    result = []
    for r in rows:
        d = {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "producto_id": r.producto_id,
            "suministro_id": r.suministro_id,
            "cantidad_necesaria": r.cantidad_necesaria,
            "activo": r.activo,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "producto_nombre": r.producto.nombre if r.producto else None,
            "suministro_nombre": r.suministro.nombre if r.suministro else None,
            "suministro_unidad": r.suministro.unidad if r.suministro else None,
        }
        result.append(d)
    return result


async def create_receta(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Receta:
    receta = Receta(tenant_id=tenant_id, **data)
    db.add(receta)
    await db.flush()
    return receta


async def delete_receta(
    db: AsyncSession, tenant_id: uuid.UUID, receta_id: uuid.UUID
) -> Receta:
    row = (await db.execute(
        select(Receta).where(
            Receta.id == receta_id, Receta.tenant_id == tenant_id
        )
    )).scalar_one_or_none()
    if not row:
        raise NotFoundError("Receta", str(receta_id))
    row.activo = False
    await db.flush()
    return row


# ── Stock decrement helpers ──

def _accumulate_item_consumption(
    item, recetas: list, consumo_acum: dict[uuid.UUID, float]
) -> None:
    """Add consumption for a single comanda item to the accumulator."""
    for receta in recetas:
        sid = receta.suministro_id
        consumo = float(receta.cantidad_necesaria) * item.cantidad
        consumo_acum[sid] = consumo_acum.get(sid, 0.0) + consumo


def _accumulate_consumption(
    comanda_items: list, recetas_by_producto: dict[uuid.UUID, list]
) -> dict[uuid.UUID, float]:
    """Build a map of suministro_id -> total consumption across all items."""
    consumo_acum: dict[uuid.UUID, float] = {}
    for item in comanda_items:
        _accumulate_item_consumption(
            item, recetas_by_producto.get(item.producto_id, []), consumo_acum
        )
    return consumo_acum


def _apply_decrements(
    consumo_acum: dict[uuid.UUID, float],
    suministro_map: dict[uuid.UUID, "Suministro"],
    tenant_id: uuid.UUID,
) -> list[dict]:
    """Apply stock decrements and return list of depleted ingredients."""
    agotados: list[dict] = []
    for sid, total_consumo in consumo_acum.items():
        suministro = suministro_map.get(sid)
        if not suministro:
            continue
        suministro.stock_actual = max(0, float(suministro.stock_actual) - total_consumo)
        if suministro.stock_actual <= 0:
            agotados.append({
                "suministro_id": str(suministro.id),
                "nombre": suministro.nombre,
            })
            logger.warning(
                "Suministro agotado: %s (tenant %s)", suministro.nombre, tenant_id
            )
    return agotados


# ── Stock decrement on delivery ──

async def decrement_ingredients_for_comanda(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_items: list
) -> list[dict]:
    """Decrement insumo stock for each item in a delivered comanda.

    Returns list of insumos that hit zero (for AI unavailability).
    Batch-fetches recetas and suministros to avoid N+1 queries.
    """
    # 1. Batch-fetch all recetas for the products in this comanda
    producto_ids = [item.producto_id for item in comanda_items]
    all_recetas = (await db.execute(
        select(Receta).where(
            Receta.tenant_id == tenant_id,
            Receta.producto_id.in_(producto_ids),
            Receta.activo.is_(True),
        )
    )).scalars().all()

    # 2. Build map: producto_id → list of recetas
    recetas_by_producto: dict[uuid.UUID, list] = {}
    suministro_ids: set[uuid.UUID] = set()
    for receta in all_recetas:
        recetas_by_producto.setdefault(receta.producto_id, []).append(receta)
        suministro_ids.add(receta.suministro_id)

    if not suministro_ids:
        return []

    # 3. Batch-fetch all suministros with FOR UPDATE
    suministros_result = (await db.execute(
        select(Suministro)
        .where(
            Suministro.id.in_(suministro_ids),
            Suministro.tenant_id == tenant_id,
        )
        .with_for_update()
    )).scalars().all()
    suministro_map = {s.id: s for s in suministros_result}

    # 4. Accumulate consumption and apply decrements
    consumo_acum = _accumulate_consumption(comanda_items, recetas_by_producto)
    agotados = _apply_decrements(consumo_acum, suministro_map, tenant_id)

    return agotados


async def get_unavailable_ingredients(
    db: AsyncSession, tenant_id: uuid.UUID
) -> dict[str, list[str]]:
    """Return map of producto_id → list of missing insumo names.

    Used by AI orchestrator to tell customers WHY a product is unavailable.
    """
    result = await db.execute(
        select(
            Receta.producto_id,
            Suministro.nombre,
        )
        .join(Suministro, Suministro.id == Receta.suministro_id)
        .where(
            Receta.tenant_id == tenant_id,
            Receta.activo.is_(True),
            Suministro.activo.is_(True),
            Suministro.stock_actual <= 0,
        )
    )

    missing: dict[str, list[str]] = {}
    for row in result.all():
        pid = str(row[0])
        missing.setdefault(pid, []).append(row[1])
    return missing
