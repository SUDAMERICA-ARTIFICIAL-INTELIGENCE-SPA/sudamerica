"""Categoria routes: POST, GET list, GET/{id}, PATCH/{id}, DELETE/{id}."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import AdminWriter, CartaReader, CartaWriter
from app.schemas.categoria import CategoriaCreate, CategoriaResponse, CategoriaUpdate
from app.services import categoria_svc

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoriaResponse)
async def create_categoria(
    body: CategoriaCreate,
    current_user: dict = CartaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new categoria."""
    return await categoria_svc.create_categoria(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.get("", response_model=PaginatedResponse[CategoriaResponse])
async def list_categorias(
    pagination: PaginationParams = Depends(),
    current_user: dict = CartaReader,
    db: AsyncSession = Depends(get_db),
):
    """List categorias for the current tenant."""
    return await categoria_svc.list_categorias(
        db, current_user["tenant_id"], pagination
    )


@router.get("/{categoria_id}", response_model=CategoriaResponse)
async def get_categoria(
    categoria_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single categoria."""
    return await categoria_svc.get_categoria(
        db, current_user["tenant_id"], categoria_id
    )


@router.patch("/{categoria_id}", response_model=CategoriaResponse)
async def update_categoria(
    categoria_id: UUID,
    body: CategoriaUpdate,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a categoria."""
    data = body.model_dump(exclude_unset=True)
    return await categoria_svc.update_categoria(
        db, current_user["tenant_id"], categoria_id, data
    )


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_categoria(
    categoria_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a categoria."""
    await categoria_svc.soft_delete_categoria(
        db, current_user["tenant_id"], categoria_id
    )
