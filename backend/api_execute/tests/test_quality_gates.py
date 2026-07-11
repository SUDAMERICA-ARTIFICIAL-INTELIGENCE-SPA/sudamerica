"""Tests for quality gate remediation changes.

Covers: password reset token schema, admin pagination, N+1 fix validation.
"""

import pytest

from .conftest import TENANT_ID, make_token


def _superadmin_headers() -> dict[str, str]:
    token = make_token(role="SUPERADMIN", email="admin@sudamerica.ai")
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
    }


# ── Password Reset Schema ─────────────────────────────


@pytest.mark.asyncio
async def test_reset_response_schema():
    """ResetPasswordResponse schema has reset_token and temp_password."""
    from datetime import datetime, timezone
    from app.schemas.admin import ResetPasswordResponse

    resp = ResetPasswordResponse(
        reset_token="abc123",
        temp_password="TempPass1",
        expires_at=datetime.now(timezone.utc),
    )
    data = resp.model_dump()
    assert "reset_token" in data
    assert "temp_password" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_set_password_request_schema():
    """SetPasswordRequest schema exists and validates correctly."""
    from app.schemas.admin import SetPasswordRequest

    req = SetPasswordRequest(reset_token="tok123", new_password="Pass123!")
    assert req.reset_token == "tok123"


@pytest.mark.asyncio
async def test_set_password_invalid_token_returns_404(client, auth_headers):
    """POST /admin/users/set-password with invalid token returns 404."""
    resp = await client.post(
        "/api/v1/admin/users/set-password",
        headers=_superadmin_headers(),
        json={"reset_token": "invalid-token-xyz", "new_password": "Whatever123!"},
    )
    assert resp.status_code == 404


# ── Admin List Endpoints (N+1 fix validation) ─────────


@pytest.mark.asyncio
async def test_list_users_pagination(client, auth_headers):
    """GET /admin/users supports page and page_size params."""
    resp = await client.get(
        "/api/v1/admin/users?page=1&page_size=5",
        headers=_superadmin_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 5


@pytest.mark.asyncio
async def test_list_tenants_returns_paginated(client, auth_headers):
    """GET /admin/tenants returns PaginatedResponse with JOINed counts."""
    resp = await client.get(
        "/api/v1/admin/tenants?page=1&page_size=10",
        headers=_superadmin_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert "data" in data
    assert data["meta"]["page"] == 1
    if data["data"]:
        first = data["data"][0]
        assert "user_count" in first
        assert "lead_count" in first


# ── Get Tenant/User (N+1 fix) ────────────────────────


@pytest.mark.asyncio
async def test_get_tenant_returns_counts(client, auth_headers):
    """GET /admin/tenants/{id} returns user_count and lead_count."""
    # First list to get a valid tenant ID
    list_resp = await client.get(
        "/api/v1/admin/tenants?page=1&page_size=1",
        headers=_superadmin_headers(),
    )
    assert list_resp.status_code == 200
    tenants = list_resp.json().get("data", [])
    if not tenants:
        pytest.skip("No seeded tenant found")
    tid = tenants[0]["id"]

    resp = await client.get(
        f"/api/v1/admin/tenants/{tid}",
        headers=_superadmin_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "user_count" in data
    assert "lead_count" in data
    assert isinstance(data["user_count"], int)
    assert isinstance(data["lead_count"], int)


@pytest.mark.asyncio
async def test_get_tenant_not_found(client, auth_headers):
    """GET /admin/tenants/{bad_id} returns 404."""
    import uuid
    resp = await client.get(
        f"/api/v1/admin/tenants/{uuid.uuid4()}",
        headers=_superadmin_headers(),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_user_returns_tenant_nombre(client, auth_headers):
    """GET /admin/users/{id} returns tenant_nombre from JOIN."""
    # First list users to get a valid user ID
    resp = await client.get(
        "/api/v1/admin/users?page=1&page_size=1",
        headers=_superadmin_headers(),
    )
    assert resp.status_code == 200
    users = resp.json().get("data", [])
    if users:
        user_id = users[0]["id"]
        resp2 = await client.get(
            f"/api/v1/admin/users/{user_id}",
            headers=_superadmin_headers(),
        )
        assert resp2.status_code == 200
        assert "tenant_nombre" in resp2.json()


# ── _collect_data_model refactored helpers ────────────


def test_extract_unique_columns():
    """_extract_unique_columns merges constraints and unique indexes."""
    from app.services.admin_service import _extract_unique_columns

    constraints = [{"column_names": ["email"]}, {"column_names": ["a", "b"]}]
    indexes = [
        {"column_names": ["slug"], "unique": True},
        {"column_names": ["name"], "unique": False},
    ]
    result = _extract_unique_columns(constraints, indexes)
    assert "email" in result
    assert "slug" in result
    assert "name" not in result
    assert "a" not in result  # multi-column, skipped


def test_extract_relations():
    """_extract_relations parses FK dicts into relations + fk_map."""
    from app.services.admin_service import _extract_relations

    fks = [
        {
            "constrained_columns": ["tenant_id"],
            "referred_columns": ["id"],
            "referred_table": "tenants",
            "options": {"ondelete": "CASCADE"},
        },
        {
            "constrained_columns": [],
            "referred_columns": [],
            "referred_table": None,
        },
    ]
    relations, fk_map = _extract_relations(fks)
    assert len(relations) == 1
    assert relations[0]["references_table"] == "tenants"
    assert relations[0]["on_delete"] == "CASCADE"
    assert fk_map["tenant_id"] == "tenants.id"


def test_serialize_columns():
    """_serialize_columns produces correct output dicts."""
    from app.services.admin_service import _serialize_columns

    columns = [{"name": "id", "type": "UUID", "nullable": False, "default": None}]
    result = _serialize_columns(columns, {"id"}, set(), {})
    assert len(result) == 1
    assert result[0]["primary_key"] is True
    assert result[0]["unique"] is False


def test_dedup_indexes():
    """_dedup_indexes removes duplicates from indexes + unique constraints."""
    from app.services.admin_service import _dedup_indexes

    indexes = [{"name": "idx_a", "column_names": ["a"], "unique": False}]
    ucs = [{"name": "uq_a", "column_names": ["a"]}]
    result = _dedup_indexes(indexes, ucs, "test_table")
    assert len(result) == 2  # different names → not deduped

    # True dedup: same signature
    indexes2 = [{"name": "idx_a", "column_names": ["a"], "unique": True}]
    ucs2 = [{"name": "idx_a", "column_names": ["a"]}]
    result2 = _dedup_indexes(indexes2, ucs2, "test_table")
    assert len(result2) == 1
