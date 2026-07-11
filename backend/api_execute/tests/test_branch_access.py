"""Tests for branch (sucursal) access control hierarchy."""

import uuid

import pytest
from fastapi import HTTPException

from shared.models.enums import UserRole
from app.routes.deps import require_branch_access, get_user_sucursal_id


SUC_A = uuid.uuid4()
SUC_B = uuid.uuid4()


# ─── require_branch_access unit tests ────────────────────────────────────────


def _user_ctx(role: str, sucursal_id: uuid.UUID | None = None) -> dict:
    return {
        "type": "user",
        "user_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "role": UserRole(role),
        "email": "test@test.com",
        "sucursal_id": sucursal_id,
        "service_name": None,
        "scopes": (),
    }


def test_superadmin_always_allowed():
    """SUPERADMIN bypasses branch check regardless of target."""
    require_branch_access(_user_ctx("SUPERADMIN"), SUC_A)
    require_branch_access(_user_ctx("SUPERADMIN"), SUC_B)
    require_branch_access(_user_ctx("SUPERADMIN"), None)


def test_global_admin_all_branches():
    """ADMIN with sucursal_id=None can access any branch."""
    require_branch_access(_user_ctx("ADMIN", sucursal_id=None), SUC_A)
    require_branch_access(_user_ctx("ADMIN", sucursal_id=None), SUC_B)
    require_branch_access(_user_ctx("ADMIN", sucursal_id=None), None)


def test_branch_admin_own_branch():
    """ADMIN with sucursal_id=A can access branch A."""
    require_branch_access(_user_ctx("ADMIN", sucursal_id=SUC_A), SUC_A)


def test_branch_admin_other_branch_403():
    """ADMIN with sucursal_id=A cannot access branch B."""
    with pytest.raises(HTTPException) as exc_info:
        require_branch_access(_user_ctx("ADMIN", sucursal_id=SUC_A), SUC_B)
    assert exc_info.value.status_code == 403


def test_personal_own_branch():
    """PERSONAL with sucursal_id=A can access branch A."""
    require_branch_access(_user_ctx("PERSONAL", sucursal_id=SUC_A), SUC_A)


def test_personal_other_branch_403():
    """PERSONAL with sucursal_id=A cannot access branch B."""
    with pytest.raises(HTTPException) as exc_info:
        require_branch_access(_user_ctx("PERSONAL", sucursal_id=SUC_A), SUC_B)
    assert exc_info.value.status_code == 403


def test_branch_user_null_target_allowed():
    """Branch-scoped user accessing target_sucursal_id=None is allowed."""
    require_branch_access(_user_ctx("PERSONAL", sucursal_id=SUC_A), None)


def test_service_token_bypasses():
    """Service tokens always bypass branch check."""
    service_ctx = {
        "type": "service",
        "user_id": None,
        "tenant_id": uuid.uuid4(),
        "role": UserRole.ADMIN,
        "service_name": "ai_dialer",
        "scopes": ("chat:write",),
    }
    require_branch_access(service_ctx, SUC_A)
    require_branch_access(service_ctx, SUC_B)


# ─── get_user_sucursal_id ───────────────────────────────────────────────────


def test_get_user_sucursal_id_present():
    ctx = _user_ctx("PERSONAL", sucursal_id=SUC_A)
    assert get_user_sucursal_id(ctx) == SUC_A


def test_get_user_sucursal_id_global_admin():
    ctx = _user_ctx("ADMIN", sucursal_id=None)
    assert get_user_sucursal_id(ctx) is None
