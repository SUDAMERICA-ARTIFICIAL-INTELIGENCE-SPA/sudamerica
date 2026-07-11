"""Usuario routes: CRUD (SUPERADMIN for create, ADMIN+ for updates)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.schemas import PaginatedResponse, PaginationParams

from app.routes.deps import SuperAdminOnly, UsuarioReader, UsuarioWriter, get_settings
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from app.services import usuario_service

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=PaginatedResponse[UsuarioResponse])
async def list_usuarios(
    pagination: PaginationParams = Depends(),
    current_user: dict = UsuarioReader,
    db: AsyncSession = Depends(get_db),
):
    """List usuarios for the current tenant."""
    return await usuario_service.list_usuarios(
        db, current_user["tenant_id"], pagination
    )


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def get_usuario(
    usuario_id: UUID,
    current_user: dict = UsuarioReader,
    db: AsyncSession = Depends(get_db),
):
    """Get a single usuario."""
    return await usuario_service.get_usuario(
        db, current_user["tenant_id"], usuario_id
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UsuarioResponse)
async def create_usuario(
    body: UsuarioCreate,
    request: Request,
    current_user: dict = SuperAdminOnly,
    db: AsyncSession = Depends(get_db),
):
    """Create a new usuario (SUPERADMIN only)."""
    settings = get_settings(request)
    return await usuario_service.create_usuario(
        db,
        current_user["tenant_id"],
        body.model_dump(),
        caller_role=current_user["role"],
        bcrypt_rounds=settings.BCRYPT_ROUNDS,
    )


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def update_usuario(
    usuario_id: UUID,
    body: UsuarioUpdate,
    current_user: dict = UsuarioWriter,
    db: AsyncSession = Depends(get_db),
):
    """Update a usuario (ADMIN+ for basic fields, SUPERADMIN for role changes).

    Sudamérica AI (open_agent) can update basic fields but cannot change
    a SUPERADMIN's role or deactivate SUPERADMIN users.
    """
    data = body.model_dump(exclude_unset=True)
    caller_role = current_user.get("role")
    is_service = current_user.get("type") == "service"
    return await usuario_service.update_usuario(
        db, current_user["tenant_id"], usuario_id, data,
        caller_role=caller_role,
        is_service_caller=is_service,
    )


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_usuario(
    usuario_id: UUID,
    current_user: dict = UsuarioWriter,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a usuario (ADMIN, SUPERADMIN, Sudamérica AI).

    Sudamérica AI cannot delete SUPERADMIN users.
    """
    is_service = current_user.get("type") == "service"
    await usuario_service.soft_delete_usuario(
        db, current_user["tenant_id"], usuario_id,
        is_service_caller=is_service,
    )
