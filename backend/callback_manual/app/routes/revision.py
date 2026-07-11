"""Revision humana endpoints — human review panel."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import CallbackSettings
from shared.database import get_db
from shared.middleware import require_role, require_user_or_service
from shared.models.enums import UserRole
from shared.schemas import PaginatedResponse, PaginationParams
from shared.utils.service_access import REVISION_CREATORS

from app.schemas.revision import (
    RevisionAccionRequest,
    RevisionCreate,
    RevisionResponse,
    RevisionStats,
)
from app.services import revision_service

router = APIRouter(tags=["revision"])


@router.post("", response_model=RevisionResponse, status_code=201)
async def create_revision(
    data: RevisionCreate,
    request: Request,
    current_user: dict = Depends(
        require_user_or_service(
            UserRole.SUPERADMIN,
            UserRole.ADMIN,
            UserRole.ASESOR,
            service_scopes=("reviews:create",),
            service_callers=REVISION_CREATORS,
        )
    ),
    session: AsyncSession = Depends(get_db),
) -> RevisionResponse:
    """Create a new review item (called by AI_dialer when confidence < threshold)."""
    settings: CallbackSettings = request.app.state.settings
    tenant_id = current_user["tenant_id"]
    revision = await revision_service.create_revision(session, tenant_id, data, settings)
    return RevisionResponse.model_validate(revision)


@router.get(
    "/pendientes",
    response_model=PaginatedResponse[RevisionResponse],
)
async def list_pendientes(
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ASESOR)),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RevisionResponse]:
    """List pending reviews for the current tenant (paginated)."""
    tenant_id = current_user["tenant_id"]
    return await revision_service.list_pendientes(session, tenant_id, pagination)


@router.get("/stats", response_model=RevisionStats)
async def get_stats(
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ASESOR)),
    session: AsyncSession = Depends(get_db),
) -> RevisionStats:
    """Get review statistics for today."""
    tenant_id = current_user["tenant_id"]
    return await revision_service.get_stats(session, tenant_id)


@router.post("/{revision_id}/aprobar", response_model=RevisionResponse)
async def aprobar(
    revision_id: UUID,
    request: Request,
    tiempo_ms: int = Query(0, ge=0),
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ASESOR)),
    session: AsyncSession = Depends(get_db),
) -> RevisionResponse:
    """Approve the AI-generated response."""
    settings: CallbackSettings = request.app.state.settings
    revision = await revision_service.aprobar(
        session=session,
        tenant_id=current_user["tenant_id"],
        revision_id=revision_id,
        operador_id=current_user["user_id"],
        tiempo_ms=tiempo_ms,
        settings=settings,
    )
    return RevisionResponse.model_validate(revision)


@router.post("/{revision_id}/editar", response_model=RevisionResponse)
async def editar(
    revision_id: UUID,
    body: RevisionAccionRequest,
    request: Request,
    tiempo_ms: int = Query(0, ge=0),
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ASESOR)),
    session: AsyncSession = Depends(get_db),
) -> RevisionResponse:
    """Edit the AI response and approve the corrected version."""
    settings: CallbackSettings = request.app.state.settings
    revision = await revision_service.editar(
        session=session,
        tenant_id=current_user["tenant_id"],
        revision_id=revision_id,
        operador_id=current_user["user_id"],
        respuesta_editada=body.respuesta_editada,
        tiempo_ms=tiempo_ms,
        settings=settings,
    )
    return RevisionResponse.model_validate(revision)


@router.post("/{revision_id}/rechazar", response_model=RevisionResponse)
async def rechazar(
    revision_id: UUID,
    tiempo_ms: int = Query(0, ge=0),
    current_user: dict = Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.ASESOR)),
    session: AsyncSession = Depends(get_db),
) -> RevisionResponse:
    """Reject the AI-generated response."""
    revision = await revision_service.rechazar(
        session=session,
        tenant_id=current_user["tenant_id"],
        revision_id=revision_id,
        operador_id=current_user["user_id"],
        tiempo_ms=tiempo_ms,
    )
    return RevisionResponse.model_validate(revision)
