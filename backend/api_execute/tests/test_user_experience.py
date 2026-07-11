"""Tests for user experience: forgot/reset password, change password, profile, email verification."""

import uuid

import pytest

from .conftest import TENANT_ID, USER_ID, make_token


VALID_PASSWORD = "NewPass1word"
REGISTER_PASSWORD = "Secure1pass"


@pytest.fixture
def auth_headers():
    token = make_token()
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": TENANT_ID}


# ── Forgot Password ─────────────────────────────────────────────────────────


async def test_forgot_password_returns_200_for_existing_email(client):
    """POST /forgot-password always returns 200 (no email leak)."""
    # Register a user first
    email = f"forgot-{uuid.uuid4().hex[:6]}@test.com"
    await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": REGISTER_PASSWORD,
        "nombre": "Forgot",
        "apellido": "Test",
        "tenant_nombre": f"ForgotCorp-{uuid.uuid4().hex[:4]}",
    })

    resp = await client.post("/api/v1/core/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    data = resp.json()
    assert "instrucciones" in data["detail"].lower() or "email" in data["detail"].lower()


async def test_forgot_password_returns_200_for_nonexistent_email(client):
    """POST /forgot-password returns 200 even for nonexistent email (no leak)."""
    resp = await client.post(
        "/api/v1/core/auth/forgot-password",
        json={"email": "nobody-ever@nonexistent.com"},
    )
    assert resp.status_code == 200


async def test_reset_password_with_invalid_token(client):
    """POST /reset-password with invalid token returns 404."""
    resp = await client.post("/api/v1/core/auth/reset-password", json={
        "token": "invalid-token-that-does-not-exist",
        "new_password": VALID_PASSWORD,
    })
    assert resp.status_code == 404


# ── Change Password ──────────────────────────────────────────────────────────


async def test_change_password_success(client):
    """POST /change-password changes password for authenticated user."""
    # Register a user
    email = f"chg-{uuid.uuid4().hex[:6]}@test.com"
    reg = await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": REGISTER_PASSWORD,
        "nombre": "Change",
        "apellido": "Pass",
        "tenant_nombre": f"ChangeCorp-{uuid.uuid4().hex[:4]}",
    })
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Change password
    resp = await client.post("/api/v1/core/auth/change-password", json={
        "current_password": REGISTER_PASSWORD,
        "new_password": VALID_PASSWORD,
    }, headers=headers)
    assert resp.status_code == 200

    # Login with new password
    login_resp = await client.post("/api/v1/core/auth/login", json={
        "email": email,
        "password": VALID_PASSWORD,
    })
    assert login_resp.status_code == 200


async def test_change_password_wrong_current(client):
    """POST /change-password with wrong current password returns 409."""
    email = f"chg2-{uuid.uuid4().hex[:6]}@test.com"
    reg = await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": REGISTER_PASSWORD,
        "nombre": "Wrong",
        "apellido": "Current",
        "tenant_nombre": f"WrongCorp-{uuid.uuid4().hex[:4]}",
    })
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.post("/api/v1/core/auth/change-password", json={
        "current_password": "WrongPass1",
        "new_password": VALID_PASSWORD,
    }, headers=headers)
    assert resp.status_code == 409


async def test_change_password_weak_new_password(client):
    """POST /change-password rejects weak new password (no uppercase)."""
    email = f"chg3-{uuid.uuid4().hex[:6]}@test.com"
    reg = await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": REGISTER_PASSWORD,
        "nombre": "Weak",
        "apellido": "Pass",
        "tenant_nombre": f"WeakCorp-{uuid.uuid4().hex[:4]}",
    })
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.post("/api/v1/core/auth/change-password", json={
        "current_password": REGISTER_PASSWORD,
        "new_password": "allowercase1",  # no uppercase
    }, headers=headers)
    assert resp.status_code == 422


# ── Profile ──────────────────────────────────────────────────────────────────


async def test_update_profile(client):
    """PATCH /profile updates nombre and apellido."""
    email = f"profile-{uuid.uuid4().hex[:6]}@test.com"
    reg = await client.post("/api/v1/core/auth/register", json={
        "email": email,
        "password": REGISTER_PASSWORD,
        "nombre": "Original",
        "apellido": "Name",
        "tenant_nombre": f"ProfileCorp-{uuid.uuid4().hex[:4]}",
    })
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.patch("/api/v1/core/auth/profile", json={
        "nombre": "Updated",
        "apellido": "Nuevo",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nombre"] == "Updated"
    assert data["apellido"] == "Nuevo"


# ── Email Verification ───────────────────────────────────────────────────────


async def test_verify_email_invalid_token(client):
    """POST /verify-email with invalid token returns 404."""
    resp = await client.post("/api/v1/core/auth/verify-email", json={
        "token": "invalid-verification-token",
    })
    assert resp.status_code == 404


async def test_resend_verification_requires_auth(client):
    """POST /resend-verification requires authentication."""
    resp = await client.post("/api/v1/core/auth/resend-verification")
    assert resp.status_code in (401, 403)


# ── Password Validation ─────────────────────────────────────────────────────


async def test_register_rejects_weak_password_no_uppercase(client):
    """Register rejects password without uppercase."""
    resp = await client.post("/api/v1/core/auth/register", json={
        "email": f"weak-{uuid.uuid4().hex[:6]}@test.com",
        "password": "nouppercase1",
        "nombre": "Weak",
        "apellido": "Test",
        "tenant_nombre": f"WeakCorp-{uuid.uuid4().hex[:4]}",
    })
    assert resp.status_code == 422


async def test_register_rejects_weak_password_no_digit(client):
    """Register rejects password without digit."""
    resp = await client.post("/api/v1/core/auth/register", json={
        "email": f"weak2-{uuid.uuid4().hex[:6]}@test.com",
        "password": "NoDigitPass",
        "nombre": "Weak",
        "apellido": "Test",
        "tenant_nombre": f"WeakCorp2-{uuid.uuid4().hex[:4]}",
    })
    assert resp.status_code == 422
