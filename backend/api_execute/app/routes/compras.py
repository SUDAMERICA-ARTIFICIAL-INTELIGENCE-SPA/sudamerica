"""Rutas del dominio Compras/Proveedores (OLA B)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse

from app.routes.deps import AdminWriter, AnyAuthenticated
from app.schemas.compras import (
    ComprasResumen,
    CotizacionResponse,
    EvaluacionProveedor,
    FacturaProveedorResponse,
    OrdenCompraResponse,
    ProveedorCreate,
    ProveedorResponse,
    ProveedorUpdate,
    RecepcionResponse,
    RequisicionResponse,
)
from app.services import compras_svc

router = APIRouter(prefix="/compras", tags=["compras"])


@router.get("/resumen", response_model=ComprasResumen)
async def resumen(current_user: dict = AnyAuthenticated, db: AsyncSession = Depends(get_db)):
    return await compras_svc.resumen(db, current_user["tenant_id"])


@router.get("/proveedores", response_model=PaginatedResponse[ProveedorResponse])
async def list_proveedores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_proveedores(
        db, current_user["tenant_id"], page=page, page_size=page_size, search=search
    )
    return PaginatedResponse.build(rows, total, page, page_size)


@router.post("/proveedores", status_code=status.HTTP_201_CREATED, response_model=ProveedorResponse)
async def create_proveedor(
    body: ProveedorCreate, current_user: dict = AdminWriter, db: AsyncSession = Depends(get_db)
):
    prov = await compras_svc.create_proveedor(db, current_user["tenant_id"], body.model_dump())
    await db.commit()
    return prov


@router.patch("/proveedores/{prov_id}", response_model=ProveedorResponse)
async def update_proveedor(
    prov_id: UUID, body: ProveedorUpdate, current_user: dict = AdminWriter, db: AsyncSession = Depends(get_db)
):
    prov = await compras_svc.update_proveedor(
        db, current_user["tenant_id"], prov_id, body.model_dump(exclude_unset=True)
    )
    await db.commit()
    return prov


@router.get("/ordenes", response_model=PaginatedResponse[OrdenCompraResponse])
async def list_ordenes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    estado: str | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_ordenes(
        db, current_user["tenant_id"], page=page, page_size=page_size, estado=estado
    )
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/ordenes/{oc_id}", response_model=OrdenCompraResponse)
async def get_orden(oc_id: UUID, current_user: dict = AnyAuthenticated, db: AsyncSession = Depends(get_db)):
    return await compras_svc.get_orden(db, current_user["tenant_id"], oc_id)


@router.get("/recepciones", response_model=PaginatedResponse[RecepcionResponse])
async def list_recepciones(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_recepciones(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/facturas", response_model=PaginatedResponse[FacturaProveedorResponse])
async def list_facturas(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    estado: str | None = Query(None),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_facturas(
        db, current_user["tenant_id"], page=page, page_size=page_size, estado=estado
    )
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/requisiciones", response_model=PaginatedResponse[RequisicionResponse])
async def list_requisiciones(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_requisiciones(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/cotizaciones", response_model=PaginatedResponse[CotizacionResponse])
async def list_cotizaciones(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = AnyAuthenticated,
    db: AsyncSession = Depends(get_db),
):
    rows, total = await compras_svc.list_cotizaciones(db, current_user["tenant_id"], page=page, page_size=page_size)
    return PaginatedResponse.build(rows, total, page, page_size)


@router.get("/evaluacion", response_model=list[EvaluacionProveedor])
async def evaluacion(current_user: dict = AnyAuthenticated, db: AsyncSession = Depends(get_db)):
    return await compras_svc.evaluacion_proveedores(db, current_user["tenant_id"])
