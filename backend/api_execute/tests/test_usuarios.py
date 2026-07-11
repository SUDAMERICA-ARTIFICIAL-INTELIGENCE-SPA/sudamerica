"""Tests for usuario routes: CRUD, role validation, plan limits."""

import uuid

import pytest

from .conftest import TENANT_ID, USER_ID, make_token


@pytest.fixture
def superadmin_headers():
    token = make_token(role="SUPERADMIN")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}


async def test_list_usuarios(client, auth_headers):
    resp = await client.get("/api/v1/core/usuarios", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1


async def test_create_usuario_requires_superadmin(client, auth_headers):
    """ADMIN cannot create users (SUPERADMIN only)."""
    body = {
        "email": f"fail-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "nombre": "Should",
        "apellido": "Fail",
        "role": "PERSONAL",
    }
    resp = await client.post("/api/v1/core/usuarios", json=body, headers=auth_headers)
    assert resp.status_code == 403


async def test_create_usuario_as_superadmin(client, superadmin_headers):
    body = {
        "email": f"new-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "nombre": "New",
        "apellido": "User",
        "role": "PERSONAL",
    }
    resp = await client.post("/api/v1/core/usuarios", json=body, headers=superadmin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == body["email"]
    assert "hashed_password" not in data


async def test_get_usuario_not_found(client, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/core/usuarios/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_usuario(client, auth_headers):
    resp = await client.patch(
        f"/api/v1/core/usuarios/{USER_ID}",
        json={"nombre": "UpdatedViaRoute"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "UpdatedViaRoute"


async def test_update_usuario_role_denied(client, auth_headers):
    """Non-SUPERADMIN cannot promote to ADMIN."""
    resp = await client.patch(
        f"/api/v1/core/usuarios/{USER_ID}",
        json={"role": "SUPERADMIN"},
        headers=auth_headers,
    )
    assert resp.status_code == 403


async def test_soft_delete_usuario(client, superadmin_headers):
    # First create a user to delete
    body = {
        "email": f"del-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "nombre": "Delete",
        "apellido": "Me",
        "role": "PERSONAL",
    }
    create_resp = await client.post("/api/v1/core/usuarios", json=body, headers=superadmin_headers)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/core/usuarios/{user_id}", headers=superadmin_headers)
    assert resp.status_code == 204
