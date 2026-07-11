"""Auth routes: register, login, refresh, forgot/reset password, change password, verify email, profile."""

import logging
from uuid import UUID

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user

from app.config import ApiExecuteSettings
from app.models.usuario import Usuario
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    FirebaseLoginRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.schemas.usuario import UsuarioResponse
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _settings(request: Request) -> ApiExecuteSettings:
    return request.app.state.settings


# ── Register & Login ─────────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Register a new tenant + admin user."""
    _, _, access, refresh = await auth_service.register(
        db,
        email=body.email,
        password=body.password,
        nombre=body.nombre,
        apellido=body.apellido,
        tenant_nombre=body.tenant_nombre,
        settings=settings,
        rubro=body.rubro,
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Login and get tokens."""
    _, access, refresh = await auth_service.login(
        db, body.email, body.password, settings
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UsuarioResponse)
async def me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the currently authenticated user."""
    result = await db.execute(
        select(Usuario).where(
            Usuario.id == current_user["user_id"],
            Usuario.activo.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


def _decode_refresh_token(token: str, settings: ApiExecuteSettings) -> tuple[str, str]:
    """Decode and validate a refresh token. Returns (user_id, tenant_id)."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not a refresh token")
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token claims")
    try:
        UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
    return user_id, tenant_id


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Refresh access token using a valid refresh token."""
    user_id, _tenant_id = _decode_refresh_token(body.refresh_token, settings)
    user_uuid = UUID(user_id)

    result = await db.execute(
        select(Usuario).where(Usuario.id == user_uuid, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")

    access = auth_service.create_access_token(
        str(user.id), str(user.tenant_id), user.role, user.email, settings
    )
    new_refresh = auth_service.create_refresh_token(
        str(user.id), str(user.tenant_id), settings
    )
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/firebase-login", response_model=TokenResponse)
async def firebase_login(
    body: FirebaseLoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Exchange a Firebase ID token for backend JWT tokens."""
    try:
        _, access, refresh = await auth_service.firebase_login(
            db, body.firebase_token, settings
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )
    return TokenResponse(access_token=access, refresh_token=refresh)


# ── Forgot / Reset Password (public, no auth required) ──────────────────────


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Send a password reset email. Always returns 200 (no email leak)."""
    result = await auth_service.create_password_reset_token(db, body.email)
    if result:
        user, token = result
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await _send_reset_email(user, reset_url, settings)
    # Always commit (even if no user found, to avoid timing attacks)
    await db.commit()
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
):
    """Reset password using a valid reset token."""
    await auth_service.reset_password_with_token(
        db, body.token, body.new_password, settings
    )
    await db.commit()
    return ResetPasswordResponse()


# ── Change Password (authenticated) ─────────────────────────────────────────


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
    current_user: dict = Depends(get_current_user),
):
    """Change password for the currently logged-in user."""
    await auth_service.change_password(
        db,
        user_id=current_user["user_id"],
        current_password=body.current_password,
        new_password=body.new_password,
        settings=settings,
    )
    await db.commit()
    return ChangePasswordResponse()


# ── Email Verification ───────────────────────────────────────────────────────


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify user's email using the token from the verification email."""
    await auth_service.verify_email_with_token(db, body.token)
    await db.commit()
    return VerifyEmailResponse()


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    db: AsyncSession = Depends(get_db),
    settings: ApiExecuteSettings = Depends(_settings),
    current_user: dict = Depends(get_current_user),
):
    """Resend email verification link for the logged-in user."""
    result = await auth_service.create_email_verification_token(
        db, current_user["user_id"]
    )
    if result:
        code, token = result.split(":", 1)
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        # Fetch user for name
        user_result = await db.execute(
            select(Usuario).where(Usuario.id == current_user["user_id"])
        )
        user = user_result.scalar_one_or_none()
        if user:
            await _send_verification_email(user, verify_url, code, settings)
    await db.commit()
    return ResendVerificationResponse()


# ── Profile Update ───────────────────────────────────────────────────────────


@router.patch("/profile", response_model=UsuarioResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update the logged-in user's name/apellido."""
    user = await auth_service.update_profile(
        db,
        user_id=current_user["user_id"],
        nombre=body.nombre,
        apellido=body.apellido,
    )
    await db.commit()
    await db.refresh(user)
    return user


# ── Email Helpers (calls tasks service) ──────────────────────────────────────


async def _send_email_via_tasks(
    to: str,
    subject: str,
    body: str,
    html: str,
    tenant_id: UUID,
    settings: ApiExecuteSettings,
) -> None:
    """Send an email via the tasks microservice (inter-service auth)."""
    from shared.middleware import build_service_auth_headers

    headers = build_service_auth_headers(
        service_name="api_execute",
        audience="tasks",
        tenant_id=tenant_id,
        secret_key=settings.INTERNAL_SERVICE_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        scopes=("email:send",),
        expires_in_seconds=settings.INTERNAL_SERVICE_TOKEN_TTL_SECONDS,
    )
    from shared.utils.http_client import internal_http

    tasks_url = f"{settings.SERVICE_TASKS_URL}/api/v1/tasks/email/send"
    await internal_http.post(
        tasks_url,
        json={"to": to, "subject": subject, "body": body, "html": html},
        headers=headers,
    )


async def _send_reset_email(
    user: Usuario, reset_url: str, settings: ApiExecuteSettings
) -> None:
    """Send password reset email via tasks service."""
    try:
        from shared.utils.email_templates import password_reset_email

        plain, html = password_reset_email(reset_url, user.nombre)
        await _send_email_via_tasks(
            to=user.email,
            subject="Restablecer contraseña — Sudamérica AI",
            body=plain,
            html=html,
            tenant_id=user.tenant_id,
            settings=settings,
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)


async def _send_verification_email(
    user: Usuario, verify_url: str, code: str, settings: ApiExecuteSettings
) -> None:
    """Send email verification via tasks service."""
    try:
        from shared.utils.email_templates import email_verification_email

        plain, html = email_verification_email(verify_url, user.nombre, code)
        await _send_email_via_tasks(
            to=user.email,
            subject="Verifica tu email — Sudamérica AI",
            body=plain,
            html=html,
            tenant_id=user.tenant_id,
            settings=settings,
        )
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)
