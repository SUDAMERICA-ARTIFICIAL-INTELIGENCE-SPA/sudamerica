"""Tests for auth_service and onboarding route coverage."""

import uuid

import pytest

from .conftest import TENANT_ID, make_token


@pytest.fixture
def superadmin_headers():
    token = make_token(role="SUPERADMIN")
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}


async def test_register_creates_tenant_and_user(client):
    """POST /register creates a new tenant + admin user + returns tokens."""
    body = {
        "email": f"reg-{uuid.uuid4().hex[:6]}@test.com",
        "password": "Secure1pass",
        "nombre": "Juan",
        "apellido": "Perez",
        "tenant_nombre": f"Pizzeria-{uuid.uuid4().hex[:4]}",
    }
    resp = await client.post("/api/v1/core/auth/register", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "access_token" in data


async def test_register_duplicate_email(client):
    """Registering with same email twice returns 409."""
    email = f"dup-{uuid.uuid4().hex[:6]}@test.com"
    body = {
        "email": email,
        "password": "Secure1pass",
        "nombre": "Ana",
        "apellido": "Lopez",
        "tenant_nombre": f"Sushi-{uuid.uuid4().hex[:4]}",
    }
    resp1 = await client.post("/api/v1/core/auth/register", json=body)
    assert resp1.status_code == 201

    body["tenant_nombre"] = f"Sushi2-{uuid.uuid4().hex[:4]}"
    resp2 = await client.post("/api/v1/core/auth/register", json=body)
    assert resp2.status_code == 409


async def test_login_valid_credentials(client):
    """Register then login with same credentials."""
    email = f"login-{uuid.uuid4().hex[:6]}@test.com"
    password = "Secure1pass"
    reg_body = {
        "email": email,
        "password": password,
        "nombre": "Login",
        "apellido": "Test",
        "tenant_nombre": f"Cafe-{uuid.uuid4().hex[:4]}",
    }
    await client.post("/api/v1/core/auth/register", json=reg_body)

    login_body = {"email": email, "password": password}
    resp = await client.post("/api/v1/core/auth/login", json=login_body)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


async def test_login_invalid_credentials(client):
    """Login with wrong password returns 404."""
    login_body = {"email": "nobody@test.com", "password": "wrongpass"}
    resp = await client.post("/api/v1/core/auth/login", json=login_body)
    assert resp.status_code == 404


async def test_refresh_token(client):
    """Use refresh token to get new access token."""
    email = f"refresh-{uuid.uuid4().hex[:6]}@test.com"
    reg_body = {
        "email": email,
        "password": "Secure1pass",
        "nombre": "Refresh",
        "apellido": "Test",
        "tenant_nombre": f"Bar-{uuid.uuid4().hex[:4]}",
    }
    reg_resp = await client.post("/api/v1/core/auth/register", json=reg_body)
    refresh_token = reg_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/core/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_me_endpoint(client, auth_headers):
    """GET /me returns current user info."""
    resp = await client.get("/api/v1/core/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
