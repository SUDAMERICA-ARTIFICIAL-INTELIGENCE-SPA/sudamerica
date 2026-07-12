"""Rutas admin del manifiesto de rubro (Fase B, Paso 5).

CRUD de plataforma para leer/editar el manifiesto de rubro persistido en la tabla global
``rubros``. Restringido a admin de plataforma (``SuperAdminOnly``), igual que ``admin_system`` /
``platform_config``: la escritura NUNCA es accesible por un tenant. Cada ``PATCH`` valida
fail-closed (422 si el manifiesto resultante es inválido), bumpea el contador global
``rubro_manifest_version`` y refresca el registro en proceso — la nueva definición se sirve sin
redeploy. El override por-tenant sigue siendo ``tenant.config`` (no vive aquí).
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_admin as get_db

from app.routes.deps import SuperAdminOnly
from app.schemas.admin_rubros import (
    RubroCreateRequest,
    RubroResponse,
    RubroUpdateRequest,
)
from app.services import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rubros", tags=["admin-rubros"])


@router.get("", response_model=list[RubroResponse])
async def list_rubros(
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los manifiestos de rubro persistidos (tabla global de referencia)."""
    return await admin_service.list_rubros(db)


@router.post("", response_model=RubroResponse, status_code=201)
async def create_rubro(
    body: RubroCreateRequest,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Crea un rubro runtime (``origen='runtime'``): valida fail-closed (422 manifiesto,
    409 key reservada/duplicada), bumpea versión, refresca registro. Solo admin de plataforma."""
    return await admin_service.create_rubro(
        db, body.model_dump(), current_user.get("user_id")
    )


@router.get("/{key}", response_model=RubroResponse)
async def get_rubro(
    key: str,
    _current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Un manifiesto de rubro por ``key`` (404 si es desconocido)."""
    return await admin_service.get_rubro(db, key)


@router.patch("/{key}", response_model=RubroResponse)
async def update_rubro(
    key: str,
    body: RubroUpdateRequest,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Edita un rubro en runtime: valida fail-closed (422), bumpea versión, refresca registro."""
    patch = body.model_dump(exclude_unset=True)
    return await admin_service.update_rubro(
        db, key, patch, current_user.get("user_id")
    )


@router.post("/{key}/desactivar", response_model=RubroResponse)
async def desactivar_rubro(
    key: str,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Desactiva un rubro runtime (``activo=false``). Rechaza (409) si es seed, si es
    ``RUBRO_DEFAULT``, o si está asignado a algún tenant. Bumpea versión y refresca registro."""
    return await admin_service.set_rubro_activo(
        db, key, False, current_user.get("user_id")
    )


@router.post("/{key}/activar", response_model=RubroResponse)
async def activar_rubro(
    key: str,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Reactiva un rubro runtime previamente desactivado (``activo=true``). Rechaza (409) si es
    un rubro seed. Bumpea versión y refresca registro."""
    return await admin_service.set_rubro_activo(
        db, key, True, current_user.get("user_id")
    )
