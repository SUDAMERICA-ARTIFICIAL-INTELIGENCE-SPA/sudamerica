"""Auth schemas: register, login, token, refresh, password reset, profile."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(password: str) -> str:
    """Enforce: min 8 chars, 1 uppercase, 1 digit."""
    if not re.search(r"[A-Z]", password):
        raise ValueError("La contraseña debe tener al menos una letra mayúscula")
    if not re.search(r"\d", password):
        raise ValueError("La contraseña debe tener al menos un número")
    return password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre: str = Field(..., min_length=1)
    apellido: str = Field(..., min_length=1)
    tenant_nombre: str = Field(..., min_length=1)
    # Rubro del negocio (multi-rubro). Opcional → fail-safe a restaurante, por lo que
    # el registro existente (sin este campo) no cambia de comportamiento.
    rubro: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class FirebaseLoginRequest(BaseModel):
    firebase_token: str


# ── Password recovery (self-service) ─────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    detail: str = "Si el email existe, recibirás instrucciones para restablecer tu contraseña."


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ResetPasswordResponse(BaseModel):
    detail: str = "Contraseña actualizada exitosamente."


# ── Change password (logged-in user) ─────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordResponse(BaseModel):
    detail: str = "Contraseña actualizada exitosamente."


# ── Email verification ───────────────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    detail: str = "Email verificado exitosamente."


class ResendVerificationResponse(BaseModel):
    detail: str = "Si tu email no está verificado, recibirás un nuevo enlace."


# ── Profile update ───────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    nombre: str | None = None
    apellido: str | None = None


class ProfileResponse(BaseModel):
    detail: str = "Perfil actualizado exitosamente."
