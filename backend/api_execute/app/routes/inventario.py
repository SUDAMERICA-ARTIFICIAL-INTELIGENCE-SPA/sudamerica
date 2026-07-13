"""Rutas de inventario derivadas (OLA B): kardex de movimientos (entradas compras / salidas ventas)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse

from app.routes.deps import AnyAuthenticated
from app.schemas.lentes import MovimientoKardex
from app.services import lentes_svc

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.get("/movimientos", response_model=PaginatedResponse[MovimientoKardex])
async def movimientos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tipo: str | None = Query(None, description="ENTRADA o SALIDA"),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """Kardex de movimientos: ENTRADA (recepciones de compra) + SALIDA (ventas)."""
    rows, total = await lentes_svc.get_movimientos(
        db, current_user["tenant_id"], page=page, page_size=page_size, tipo=tipo
    )
    return PaginatedResponse.build(rows, total, page, page_size)
