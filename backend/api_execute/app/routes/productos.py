"""Producto routes: CRUD + filters + reactivar + imagen."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import AdminWriter, CartaReader, CartaWriter, get_settings
from app.schemas.producto import ProductoCreate, ProductoResponse, ProductoUpdate
from app.services import producto_svc

router = APIRouter(prefix="/productos", tags=["productos"])

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductoResponse)
async def create_producto(
    body: ProductoCreate,
    current_user: dict = CartaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Create a new producto."""
    return await producto_svc.create_producto(
        db, current_user["tenant_id"], body.model_dump()
    )


@router.get("", response_model=PaginatedResponse[ProductoResponse])
async def list_productos(
    pagination: PaginationParams = Depends(),
    categoria_id: UUID | None = Query(None),
    precio_min: Decimal | None = Query(None),
    precio_max: Decimal | None = Query(None),
    nombre: str | None = Query(None),
    disponible: bool | None = Query(None),
    current_user: dict = CartaReader,
    db: AsyncSession = Depends(get_db),
):
    """List productos with optional filters."""
    return await producto_svc.list_productos(
        db, current_user["tenant_id"], pagination,
        categoria_id=categoria_id,
        precio_min=precio_min,
        precio_max=precio_max,
        nombre=nombre,
        disponible=disponible,
    )


@router.get("/{producto_id}", response_model=ProductoResponse)
async def get_producto(
    producto_id: UUID,
    current_user: dict = CartaReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single producto."""
    return await producto_svc.get_producto(
        db, current_user["tenant_id"], producto_id
    )


@router.patch("/{producto_id}", response_model=ProductoResponse)
async def update_producto(
    producto_id: UUID,
    body: ProductoUpdate,
    current_user: dict = CartaWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a producto."""
    data = body.model_dump(exclude_unset=True)
    return await producto_svc.update_producto(
        db, current_user["tenant_id"], producto_id, data
    )


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_producto(
    producto_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a producto."""
    await producto_svc.soft_delete_producto(
        db, current_user["tenant_id"], producto_id
    )


@router.patch("/{producto_id}/activar", response_model=ProductoResponse)
async def reactivar_producto(
    producto_id: UUID,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a soft-deleted producto."""
    return await producto_svc.reactivar_producto(
        db, current_user["tenant_id"], producto_id
    )


@router.post("/{producto_id}/imagen", response_model=ProductoResponse)
async def upload_producto_image(
    producto_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Upload an image for a producto. Stores in GCS, updates imagen_url."""
    from app.services import image_storage_svc

    tenant_id = current_user["tenant_id"]
    settings = get_settings(request)

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "Imagen muy grande (máx 5 MB)")
    if not content:
        raise HTTPException(400, "Archivo vacío")

    ct = file.content_type or "image/jpeg"

    try:
        public_url = await image_storage_svc.upload_product_image(
            tenant_id=tenant_id,
            producto_id=producto_id,
            file_content=content,
            content_type=ct,
            gcs_bucket_name=settings.GCS_BUCKET_NAME,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(501, str(exc))

    return await producto_svc.update_producto(
        db, tenant_id, producto_id, {"imagen_url": public_url}
    )


@router.delete("/{producto_id}/imagen", status_code=status.HTTP_204_NO_CONTENT)
async def delete_producto_image(
    producto_id: UUID,
    request: Request,
    current_user: dict = AdminWriter,
    db: AsyncSession = Depends(get_db),
):
    """Delete a producto's image from GCS and clear imagen_url."""
    from app.services import image_storage_svc

    tenant_id = current_user["tenant_id"]
    settings = get_settings(request)

    await image_storage_svc.delete_product_image(
        tenant_id=tenant_id,
        producto_id=producto_id,
        gcs_bucket_name=settings.GCS_BUCKET_NAME,
    )
    await producto_svc.update_producto(
        db, tenant_id, producto_id, {"imagen_url": None}
    )
