"""Tests for auth: register, login, refresh, duplicate handling."""

import uuid

import pytest

from .conftest import auth_headers

@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/v1/core/auth/register", json={
        "email": "new@test.com",
        "password": "Secure1pass",
        "nombre": "Test",
        "apellido": "User",
        "tenant_nombre": "TestCorp",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "dupe@test.com",
        "password": "Secure1pass",
        "nombre": "Test",
        "apellido": "User",
        "tenant_nombre": "DupeCorp",
    }
    resp1 = await client.post("/api/v1/core/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/core/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    email = "login@test.com"
    password = "Secure1pass"
    await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": password,
        "nombre": "Login",
        "apellido": "User",
        "tenant_nombre": "LoginCorp",
    })

    resp = await client.post("/api/v1/core/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email = "wrong@test.com"
    await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": "Secure1pass",
        "nombre": "Wrong",
        "apellido": "User",
        "tenant_nombre": "WrongCorp",
    })

    resp = await client.post("/api/v1/core/auth/login", json={
        "email": email,
        "password": "badpassword",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_refresh(client):
    email = "refresh@test.com"
    reg = await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": "Secure1pass",
        "nombre": "Refresh",
        "apellido": "User",
        "tenant_nombre": "RefreshCorp",
    })
    tokens = reg.json()

    resp = await client.post("/api/v1/core/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_authenticated_request_rejects_tenant_header_mismatch(client, auth_headers):
    mismatched_headers = dict(auth_headers)
    mismatched_headers["X-Tenant-ID"] = str(uuid.uuid4())

    resp = await client.get("/api/v1/core/categorias", headers=mismatched_headers)
    assert resp.status_code == 403
