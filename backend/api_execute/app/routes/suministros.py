"""Suministros (insumos genéricos) + Recetas (BOM ítem-insumo) routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse

from app.routes.deps import AdminWriter, AnyAuthenticated
from app.schemas.suministro import (
    RecetaCreate,
    RecetaResponse,
    SuministroCreate,
    SuministroResponse,
    SuministroUpdate,
)
from app.services import suministro_svc

router = APIRouter(prefix="/suministros", tags=["suministros"])


# ── Suministros CRUD ──

@router.get("", response_model=PaginatedResponse[SuministroResponse])
async def list_suministros(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List all active ingredients."""
    rows, total = await suministro_svc.list_suministros(
        db, current_user["tenant_id"], page=page, page_size=page_size
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": [SuministroResponse.model_validate(r) for r in rows],
        "meta": {"total": total, "page": page, "page_size": page_size, "total_pages": total_pages},
    }


@router.post("", response_model=SuministroResponse, status_code=status.HTTP_201_CREATED)
async def create_suministro(
    body: SuministroCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new ingredient."""
    row = await suministro_svc.create_suministro(
        db, current_user["tenant_id"], body.model_dump()
    )
    await db.commit()
    return SuministroResponse.model_validate(row)


@router.patch("/{suministro_id}", response_model=SuministroResponse)
async def update_suministro(
    suministro_id: UUID,
    body: SuministroUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update an ingredient (stock, cost, supplier, etc.)."""
    row = await suministro_svc.update_suministro(
        db, current_user["tenant_id"], suministro_id,
        body.model_dump(exclude_unset=True),
    )
    await db.commit()
    return SuministroResponse.model_validate(row)


@router.delete("/{suministro_id}", response_model=SuministroResponse)
async def delete_suministro(
    suministro_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an ingredient."""
    row = await suministro_svc.delete_suministro(
        db, current_user["tenant_id"], suministro_id
    )
    await db.commit()
    return SuministroResponse.model_validate(row)


# ── Recetas ──

@router.get("/recetas", response_model=list[RecetaResponse])
async def list_recetas(
    producto_id: UUID | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    """List recipes (product-ingredient links)."""
    rows = await suministro_svc.list_recetas(
        db, current_user["tenant_id"], producto_id=producto_id
    )
    return rows


@router.post("/recetas", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED)
async def create_receta(
    body: RecetaCreate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Link an ingredient to a product (recipe)."""
    row = await suministro_svc.create_receta(
        db, current_user["tenant_id"], body.model_dump()
    )
    await db.commit()
    # Re-fetch with relationships
    recetas = await suministro_svc.list_recetas(
        db, current_user["tenant_id"], producto_id=row.producto_id
    )
    return next((r for r in recetas if r["id"] == row.id), recetas[0])


@router.delete("/recetas/{receta_id}")
async def delete_receta(
    receta_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Remove an ingredient from a product recipe."""
    await suministro_svc.delete_receta(db, current_user["tenant_id"], receta_id)
    await db.commit()
    return {"ok": True}
