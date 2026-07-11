"""Comanda service: CRUD + FSM transitions + KDS view."""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comanda import Comanda, ComandaItem
from app.models.modifier import Modifier
from app.models.producto import Producto
from app.models.smart_alert import SmartAlert
from app.services.fidelizacion_svc import update_lead_stats
from app.services.inventario_rules import (
    ALERTA_STOCK_BAJO,
    cruza_stock_minimo,
    mensaje_stock_bajo,
)
from app.services.rubro_prompt import incluye_capacidad
from app.services.tenant_rubro import load_tenant_rubro
from app.services.venta_svc import create_venta
from shared.models.enums import ComandaEstado
from shared.rubros import Capacidad, Primitiva, puede_transicionar, rubro_def
from shared.schemas import PaginatedResponse, PaginationParams
from shared.services import crud
from shared.utils.exceptions import InvalidTransitionError, NotFoundError

logger = logging.getLogger(__name__)


def _comanda_eager_query():
    """Base select for Comanda with eagerly loaded items + producto + cliente."""
    return select(Comanda).options(
        selectinload(Comanda.items).selectinload(ComandaItem.producto),
        selectinload(Comanda.cliente),
    )


def _apply_comanda_filters(base, *, sucursal_id=None, estado=None,
                           tipo_entrega=None, canal_origen=None,
                           fecha_desde=None, fecha_hasta=None,
                           cliente_id=None):
    """Apply optional WHERE filters to a comanda query.

    Clauses are guarded individually — they can't live in a tuple list
    because SQLAlchemy evaluates ``Column >= None`` eagerly at construction
    time and raises ``ArgumentError``.
    """
    if sucursal_id is not None:
        base = base.where(Comanda.sucursal_id == sucursal_id)
    if estado:
        base = base.where(Comanda.estado == estado)
    if tipo_entrega:
        base = base.where(Comanda.tipo_entrega == tipo_entrega)
    if canal_origen:
        base = base.where(Comanda.canal_origen == canal_origen)
    if fecha_desde is not None:
        base = base.where(Comanda.created_at >= fecha_desde)
    if fecha_hasta is not None:
        base = base.where(Comanda.created_at <= fecha_hasta)
    if cliente_id is not None:
        base = base.where(Comanda.cliente_id == cliente_id)
    return base


async def list_comandas(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
    estado: str | None = None,
    tipo_entrega: str | None = None,
    canal_origen: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    sucursal_id: uuid.UUID | None = None,
    cliente_id: uuid.UUID | None = None,
    order_desc: bool = False,
) -> PaginatedResponse:
    """List comandas with optional filters, optionally scoped by sucursal.

    ``order_desc`` flips to reverse-chronological (most recent first), used by
    the "lo de siempre" flow which needs the newest deliveries on top.
    """
    base = select(Comanda).where(Comanda.tenant_id == tenant_id, Comanda.activo.is_(True))
    base = _apply_comanda_filters(
        base, sucursal_id=sucursal_id, estado=estado, tipo_entrega=tipo_entrega,
        canal_origen=canal_origen, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        cliente_id=cliente_id,
    )

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

    order_clause = (
        (Comanda.created_at.desc(),)
        if order_desc
        else (Comanda.prioridad.desc(), Comanda.created_at.asc())
    )
    rows = await db.execute(
        base.options(
            selectinload(Comanda.items).selectinload(ComandaItem.producto),
            selectinload(Comanda.cliente),
        )
        .order_by(*order_clause)
        .offset(pagination.offset).limit(pagination.page_size)
    )
    enriched = [enrich_comanda(c) for c in rows.scalars().unique().all()]
    return PaginatedResponse.build(
        items=enriched, total=total, page=pagination.page, page_size=pagination.page_size,
    )


async def get_comanda(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_id: uuid.UUID
) -> Comanda:
    """Get a single active comanda with eagerly loaded relationships."""
    result = await db.execute(
        _comanda_eager_query()
        .where(
            Comanda.id == comanda_id,
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
        )
    )
    comanda = result.scalars().unique().first()
    if not comanda:
        raise NotFoundError("Comanda", str(comanda_id))
    return comanda


def _resolve_modifiers(
    mod_entries: list[dict], lookup: dict[uuid.UUID, "Modifier"]
) -> list[dict]:
    """Resolve modifier entries against the lookup, returning snapshot dicts."""
    result = []
    for entry in mod_entries:
        mid = entry.get("modifier_id")
        if not mid:
            continue
        modifier = lookup.get(uuid.UUID(str(mid)))
        if modifier:
            result.append({
                "modifier_id": str(modifier.id),
                "nombre": modifier.nombre,
                "precio_delta": float(modifier.precio_delta),
            })
    return result


def _build_delivery_sale_note(comanda: Comanda, item_index: int) -> str:
    """Create an audit-friendly note for ventas generated from a comanda."""
    parts = []
    if comanda.notas:
        parts.append(comanda.notas)
    parts.append(f"COMANDA:{comanda.id}")
    parts.append(f"ITEM:{item_index}")
    return " | ".join(parts)


async def _decrement_ingredients(
    db: AsyncSession, tenant_id: uuid.UUID, comanda: Comanda
) -> None:
    """Decrement ingredient stock for delivered comanda items."""
    try:
        from app.services.suministro_svc import decrement_ingredients_for_comanda
        await decrement_ingredients_for_comanda(db, tenant_id, comanda.items)
    except Exception:
        # Non-blocking: ingredient tracking is optional
        pass


def _alerta_stock_bajo(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    producto: Producto,
    stock_antes: int,
    rubro_key: str,
) -> None:
    """SmartAlert ``stock_bajo`` al cruzar el umbral; nunca bloquea la entrega."""
    if not cruza_stock_minimo(stock_antes, producto.stock, producto.stock_minimo):
        return
    try:
        db.add(SmartAlert(
            tenant_id=tenant_id,
            tipo=ALERTA_STOCK_BAJO,
            mensaje=mensaje_stock_bajo(
                producto.nombre,
                producto.stock,
                producto.stock_minimo,
                item_label=rubro_def(rubro_key).labels[Primitiva.ITEM],
            ),
        ))
    except Exception:
        logger.warning(
            "No se pudo crear alerta stock_bajo (tenant %s)", tenant_id, exc_info=True
        )


async def _decrement_stock(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    comanda: Comanda,
    rubro_key: str | None = None,
) -> None:
    """Decrement producto stock for each item in a delivered comanda.

    F3 multi-rubro: si el rubro tiene la capacidad `inventario` (stock por ítem), un
    cruce del umbral ``stock_minimo`` genera una SmartAlert ``stock_bajo``.
    Restaurante tiene `inventario` OFF → comportamiento byte-idéntico.
    """
    if rubro_key is None:
        rubro_key = await load_tenant_rubro(db, tenant_id)
    inventario_on = incluye_capacidad(rubro_key, Capacidad.INVENTARIO)
    for item in comanda.items:
        await db.execute(
            select(Producto).where(
                Producto.id == item.producto_id,
                Producto.tenant_id == tenant_id,
            ).with_for_update()
        )
        result = await db.execute(
            select(Producto).where(
                Producto.id == item.producto_id,
                Producto.tenant_id == tenant_id,
            )
        )
        producto = result.scalar_one_or_none()
        if producto and producto.stock > 0:
            stock_antes = producto.stock
            producto.stock = max(0, producto.stock - item.cantidad)
            if producto.stock == 0:
                producto.disponible = False
            if inventario_on:
                _alerta_stock_bajo(db, tenant_id, producto, stock_antes, rubro_key)


async def _sync_delivery_sales(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    comanda: Comanda,
) -> None:
    """Create ventas from delivered comanda items once per comanda."""
    if comanda.venta_id or not comanda.items:
        return

    first_venta_id = None
    for index, item in enumerate(comanda.items, start=1):
        venta = await create_venta(
            db,
            tenant_id,
            usuario_id,
            {
                "lead_id": comanda.cliente_id,
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
                "precio_unitario": Decimal(str(item.precio_unitario)),
                "notas": _build_delivery_sale_note(comanda, index),
                "tipo_entrega": comanda.tipo_entrega,
                "numero_mesa": comanda.numero_mesa,
            },
        )
        if first_venta_id is None:
            first_venta_id = venta.id

    # venta_id remains a single FK for backward compatibility, so store the first linked sale.
    comanda.venta_id = first_venta_id

def _compute_priority(data: dict) -> int:
    """Compute comanda priority based on delivery type and channel."""
    tipo = data.get("tipo_entrega", "MESA")
    canal = data.get("canal_origen", "PRESENCIAL")
    priority = {"DELIVERY": 2, "RETIRO": 1}.get(tipo, 0)
    if canal == "WHATSAPP":
        priority += 1
    return priority


async def _fetch_modifier_lookup(
    db: AsyncSession, tenant_id: uuid.UUID, items_data: list[dict],
) -> dict[uuid.UUID, "Modifier"]:
    """Batch-fetch all referenced modifiers in one query."""
    all_mod_ids = {
        uuid.UUID(str(me.get("modifier_id")))
        for item_data in items_data
        for me in item_data.get("modifiers_json", [])
        if me.get("modifier_id")
    }
    if not all_mod_ids:
        return {}
    mod_result = await db.execute(
        select(Modifier).where(
            Modifier.id.in_(all_mod_ids),
            Modifier.tenant_id == tenant_id,
            Modifier.activo.is_(True),
        )
    )
    return {m.id: m for m in mod_result.scalars().all()}


async def _create_comanda_item(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_id: uuid.UUID,
    item_data: dict, modifier_lookup: dict[uuid.UUID, "Modifier"],
) -> None:
    """Create a single ComandaItem with resolved pricing."""
    producto = await crud.get_by_id(db, Producto, tenant_id, item_data["producto_id"], label="Producto")
    base_price = Decimal(str(producto.precio))
    modifiers_snapshot = _resolve_modifiers(item_data.get("modifiers_json", []), modifier_lookup)
    modifier_total = sum(Decimal(str(m["precio_delta"])) for m in modifiers_snapshot)
    precio_unitario = base_price + modifier_total
    cantidad = item_data.get("cantidad", 1)
    costo_unitario = float(producto.costo) if producto.costo else None
    comanda_item = ComandaItem(
        comanda_id=comanda_id,
        producto_id=item_data["producto_id"],
        cantidad=cantidad,
        precio_unitario=float(precio_unitario),
        costo_unitario=costo_unitario,
        modifiers_json=modifiers_snapshot,
        subtotal=float(precio_unitario * cantidad),
        notas=item_data.get("notas"),
    )
    db.add(comanda_item)


async def create_comanda(
    db: AsyncSession, tenant_id: uuid.UUID, data: dict
) -> Comanda:
    """Create a comanda with items, computing prices from products + modifiers."""
    items_data = data.pop("items", [])
    if not items_data:
        raise ValueError("A comanda must have at least one item")

    if "prioridad" not in data or data.get("prioridad", 0) == 0:
        data["prioridad"] = _compute_priority(data)

    comanda = Comanda(tenant_id=tenant_id, **data)
    db.add(comanda)
    await db.flush()

    modifier_lookup = await _fetch_modifier_lookup(db, tenant_id, items_data)
    for item_data in items_data:
        await _create_comanda_item(db, tenant_id, comanda.id, item_data, modifier_lookup)
    await db.flush()

    result = await db.execute(_comanda_eager_query().where(Comanda.id == comanda.id))
    return result.scalars().unique().first()


async def transition_estado(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    comanda_id: uuid.UUID,
    target_estado: str,
    usuario_id: uuid.UUID | None = None,
) -> Comanda:
    """FSM transition: valida contra el FSM del rubro (F4 multi-rubro).

    Restaurante usa el FSM clásico (sincronizado con ``ComandaEstado.valid_transitions``,
    test en shared/tests/test_operativa.py); rubros sin cocina usan el FSM genérico con
    ``EN_PROCESO``. Estados inválidos ahora fallan como ``InvalidTransitionError``
    (antes ``ValueError`` sin manejar).
    """
    comanda = await get_comanda(db, tenant_id, comanda_id)
    rubro_key = await load_tenant_rubro(db, tenant_id)

    if not puede_transicionar(rubro_key, comanda.estado, target_estado):
        raise InvalidTransitionError(comanda.estado, target_estado)

    comanda.estado = target_estado

    # Set entregado_at when transitioning to ENTREGADO
    if target_estado == ComandaEstado.ENTREGADO.value:
        comanda.entregado_at = datetime.now(timezone.utc)
        await _sync_delivery_sales(db, tenant_id, usuario_id, comanda)
        await _decrement_stock(db, tenant_id, comanda, rubro_key=rubro_key)
        await _decrement_ingredients(db, tenant_id, comanda)
        # Trigger fidelizacion stats update
        await update_lead_stats(db, tenant_id, comanda)

    await db.flush()
    return comanda


async def get_kds_view(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sucursal_id: uuid.UUID | None = None,
) -> dict:
    """KDS view: comandas grouped by estado (PENDIENTE + EN_COCINA + LISTO)."""
    kds_estados = [
        ComandaEstado.PENDIENTE.value,
        ComandaEstado.EN_COCINA.value,
        ComandaEstado.LISTO.value,
    ]

    query = (
        _comanda_eager_query()
        .where(
            Comanda.tenant_id == tenant_id,
            Comanda.activo.is_(True),
            Comanda.estado.in_(kds_estados),
        )
        .order_by(Comanda.prioridad.desc(), Comanda.created_at.asc())
    )
    if sucursal_id is not None:
        query = query.where(Comanda.sucursal_id == sucursal_id)

    result = await db.execute(query)
    comandas = list(result.scalars().unique().all())

    grouped: dict[str, list] = {
        "PENDIENTE": [],
        "EN_COCINA": [],
        "LISTO": [],
    }
    for comanda in comandas:
        enriched = enrich_comanda(comanda)
        grouped[comanda.estado].append(enriched)

    return grouped


async def soft_delete_comanda(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_id: uuid.UUID
) -> Comanda:
    """Soft-delete a comanda."""
    return await crud.soft_delete(db, Comanda, tenant_id, comanda_id, label="Comanda")


def enrich_comanda(comanda: Comanda) -> dict:
    """Enrich comanda with client name and product names in items."""
    data = {
        "id": comanda.id,
        "tenant_id": comanda.tenant_id,
        "venta_id": comanda.venta_id,
        "cliente_id": comanda.cliente_id,
        "tipo_entrega": comanda.tipo_entrega,
        "numero_mesa": comanda.numero_mesa,
        "estado": comanda.estado,
        "canal_origen": comanda.canal_origen,
        "notas": comanda.notas,
        "prioridad": comanda.prioridad,
        "tiempo_estimado_min": comanda.tiempo_estimado_min,
        "activo": comanda.activo,
        "created_at": comanda.created_at,
        "updated_at": comanda.updated_at,
        "entregado_at": comanda.entregado_at,
        "cliente_nombre": None,
        "items": [],
    }

    if comanda.cliente:
        data["cliente_nombre"] = comanda.cliente.nombre

    for item in comanda.items:
        item_data = {
            "id": item.id,
            "comanda_id": item.comanda_id,
            "producto_id": item.producto_id,
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "modifiers_json": item.modifiers_json,
            "subtotal": item.subtotal,
            "notas": item.notas,
            "producto_nombre": item.producto.nombre if item.producto else None,
        }
        data["items"].append(item_data)

    return data


