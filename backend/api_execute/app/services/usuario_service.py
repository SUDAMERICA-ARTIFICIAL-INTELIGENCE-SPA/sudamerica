"""Usuario service: CRUD + plan limits + role validation."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enums import UserRole
from shared.schemas import PaginatedResponse, PaginationParams
from shared.utils.exceptions import ConflictError, ForbiddenError, NotFoundError

from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.services.auth_service import hash_password

# Roles that only SUPERADMIN can assign
_PRIVILEGED_ROLES = {UserRole.ADMIN.value, UserRole.SUPERADMIN.value}


async def list_usuarios(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    pagination: PaginationParams,
) -> PaginatedResponse:
    """List active usuarios for a tenant."""
    base = select(Usuario).where(
        Usuario.tenant_id == tenant_id, Usuario.activo.is_(True)
    )
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    rows = await db.execute(
        base.offset(pagination.offset).limit(pagination.page_size)
    )
    items = list(rows.scalars().all())
    return PaginatedResponse.build(
        items=items, total=total,
        page=pagination.page, page_size=pagination.page_size,
    )


async def get_usuario(
    db: AsyncSession, tenant_id: uuid.UUID, usuario_id: uuid.UUID
) -> Usuario:
    """Get a single usuario by ID."""
    result = await db.execute(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.tenant_id == tenant_id,
            Usuario.activo.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", str(usuario_id))
    return user


async def create_usuario(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: dict,
    caller_role: UserRole | str | None = None,
    bcrypt_rounds: int = 12,
) -> Usuario:
    """Create usuario, enforcing max_users per plan and role restrictions."""
    tenant_r = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_r.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant", str(tenant_id))

    # Lazy plan enforcement: downgrade if a failed-payment grace window expired,
    # so max_users below reflects the plan the tenant actually pays for.
    from app.services.mercadopago_service import apply_pending_downgrade
    apply_pending_downgrade(tenant)

    # Only SUPERADMIN can assign ADMIN or SUPERADMIN roles
    target_role = data.get("role", "PERSONAL")
    _validate_role_assignment(caller_role, target_role)

    count_q = select(func.count()).where(
        Usuario.tenant_id == tenant_id, Usuario.activo.is_(True)
    )
    count = (await db.execute(count_q)).scalar() or 0
    if count >= tenant.max_users:
        raise ConflictError(
            f"Max users ({tenant.max_users}) reached for plan {tenant.plan}"
        )

    password = data.pop("password")
    user = Usuario(
        tenant_id=tenant_id,
        hashed_password=hash_password(password, bcrypt_rounds),
        **data,
    )
    db.add(user)
    await db.flush()
    return user


async def update_usuario(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    data: dict,
    caller_role: UserRole | str | None = None,
    is_service_caller: bool = False,
) -> Usuario:
    """Update usuario fields.

    Accepts dict from model_dump(exclude_unset=True): keys present means
    the client explicitly sent them, so None is a valid value (clear field).
    Only SUPERADMIN can change the role field to ADMIN or SUPERADMIN.
    Service callers (Sudamérica AI) cannot modify SUPERADMIN users' role or activo.
    """
    user = await get_usuario(db, tenant_id, usuario_id)

    # Safeguard: services (Sudamérica AI) cannot touch SUPERADMIN privileges
    if is_service_caller and user.role == UserRole.SUPERADMIN.value:
        if "role" in data or "activo" in data:
            raise ForbiddenError(
                "Sudamérica AI cannot modify SUPERADMIN role or status"
            )

    # Validate role change if present
    if "role" in data and data["role"] is not None:
        _validate_role_assignment(caller_role, data["role"])

    for key, value in data.items():
        setattr(user, key, value)
    await db.flush()
    return user


async def soft_delete_usuario(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    is_service_caller: bool = False,
) -> Usuario:
    """Soft-delete a usuario by setting activo=False.

    Service callers (Sudamérica AI) cannot delete SUPERADMIN users.
    """
    user = await get_usuario(db, tenant_id, usuario_id)

    if is_service_caller and user.role == UserRole.SUPERADMIN.value:
        raise ForbiddenError(
            "Sudamérica AI cannot deactivate SUPERADMIN users"
        )

    user.activo = False
    await db.flush()
    return user


def _validate_role_assignment(
    caller_role: UserRole | str | None,
    target_role: str,
) -> None:
    """Only SUPERADMIN can assign ADMIN or SUPERADMIN roles."""
    if target_role in _PRIVILEGED_ROLES:
        caller_str = caller_role.value if isinstance(caller_role, UserRole) else caller_role
        if caller_str != UserRole.SUPERADMIN.value:
            raise ForbiddenError(
                f"Only SUPERADMIN can assign role {target_role}"
            )
