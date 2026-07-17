"""Rutas de dominios chicos de OLA B (B3): devoluciones, plantillas, documentos, campañas."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse

from app.routes.deps import AdminWriter, AnyAuthenticated
from app.schemas.olab_crud import (
    CampanaCreate,
    CampanaResponse,
    DevolucionResponse,
    DocumentoResponse,
    PlantillaCreate,
    PlantillaResponse,
)
from app.services import olab_crud_svc

router = APIRouter(tags=["olab"])


@router.get("/devoluciones", response_model=PaginatedResponse[DevolucionResponse])
async def list_devoluciones(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await olab_crud_svc.list_devoluciones(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/plantillas", response_model=PaginatedResponse[PlantillaResponse])
async def list_plantillas(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await olab_crud_svc.list_plantillas(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.post("/plantillas", status_code=status.HTTP_201_CREATED, response_model=PlantillaResponse)
async def create_plantilla(
    body: PlantillaCreate, current_user: dict = AdminWriter, db: AsyncSession = Depends(get_db)
):
    row = await olab_crud_svc.create_plantilla(db, current_user["tenant_id"], body.model_dump())
    await db.commit()
    return row


@router.get("/documentos", response_model=PaginatedResponse[DocumentoResponse])
async def list_documentos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tipo: str | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await olab_crud_svc.list_documentos(
        db, current_user["tenant_id"], page=page, page_size=page_size, tipo=tipo
    )
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/campanas", response_model=PaginatedResponse[CampanaResponse])
async def list_campanas(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await olab_crud_svc.list_campanas(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.post("/campanas", status_code=status.HTTP_201_CREATED, response_model=CampanaResponse)
async def create_campana(
    body: CampanaCreate, current_user: dict = AdminWriter, db: AsyncSession = Depends(get_db)
):
    row = await olab_crud_svc.create_campana(db, current_user["tenant_id"], body.model_dump())
    await db.commit()
    return row
