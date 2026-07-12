"""Authentication service: password hashing, JWT, register, login, Firebase, password reset."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt as pyjwt
from cryptography.x509 import load_pem_x509_certificate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import set_tenant_context
from shared.models.enums import TenantPlan, UserRole
from shared.utils.exceptions import ConflictError, NotFoundError

from app.config import ApiExecuteSettings
from app.models.categoria import Categoria
from app.models.password_reset_token import PasswordResetToken
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.services.tenant_service import generate_slug
from shared.rubros import RUBRO_DEFAULT, resolve_rubro

# Fase B (Paso 5): rubro_def desde el registro DB-backed (fallback puro a diccionario.py).
from app.services.rubro_registry import rubro_def

from app.schemas.tenant_config import validate_tenant_config

logger = logging.getLogger(__name__)

RESET_TOKEN_TTL_MINUTES = 60
VERIFY_TOKEN_TTL_MINUTES = 1440  # 24 hours

# Firebase ID token verification
GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
FIREBASE_PROJECT_ID = "siavanza-d9722"
_cached_certs: dict[str, str] | None = None


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    email: str,
    settings: ApiExecuteSettings,
    sucursal_id: str | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRATION_MINUTES
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "exp": expires,
        "type": "access",
    }
    if sucursal_id is not None:
        payload["sucursal_id"] = sucursal_id
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    settings: ApiExecuteSettings,
) -> str:
    """Create a long-lived JWT refresh token."""
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRATION_DAYS
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expires,
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def register(
    db: AsyncSession,
    email: str,
    password: str,
    nombre: str,
    apellido: str,
    tenant_nombre: str,
    settings: ApiExecuteSettings,
    rubro: str | None = None,
) -> tuple[Tenant, Usuario, str, str]:
    """Register a new tenant (ESTANDAR) and its first ADMIN user."""
    existing = await db.execute(
        select(Usuario).where(Usuario.email == email)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Email '{email}' already registered")

    # Rubro (multi-rubro): fail-closed en publicación. Un rubro provisto pero desconocido
    # se rechaza (422) en vez de degradar en silencio a restaurante. `rubro=None` (no
    # especificado) sí resuelve a restaurante por defecto. El sector se deriva del rubro.
    validate_tenant_config({"rubro": rubro})
    rubro_key = resolve_rubro({"rubro": rubro})
    rdef = rubro_def(rubro_key)

    plan = TenantPlan.ESTANDAR
    tenant = Tenant(
        nombre=tenant_nombre,
        slug=generate_slug(tenant_nombre),
        plan=plan.value,
        max_users=plan.max_users,
        max_leads_mes=plan.max_leads_mes,
        config={
            "sector": rdef.sector,
            "rubro": rubro_key,
            "onboarding": {
                "required": True,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )
    db.add(tenant)
    await db.flush()

    # Set RLS context so the INSERT on usuarios passes the tenant_isolation policy
    await set_tenant_context(db, str(tenant.id))

    # Siembra categorías-plantilla para rubros no-gastronómicos, para que el negocio
    # quede operable de inmediato. Restaurante conserva su flujo actual (sin sembrar:
    # sus categorías se crean al importar el menú).
    if rubro_key != RUBRO_DEFAULT and rdef.categorias_semilla:
        for nombre_categoria in rdef.categorias_semilla:
            db.add(Categoria(tenant_id=tenant.id, nombre=nombre_categoria))
        await db.flush()

    user = Usuario(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password(password, settings.BCRYPT_ROUNDS),
        nombre=nombre,
        apellido=apellido,
        role=UserRole.ADMIN.value,
    )
    db.add(user)
    await db.flush()

    access = create_access_token(
        str(user.id), str(tenant.id), user.role, user.email, settings
    )
    refresh = create_refresh_token(str(user.id), str(tenant.id), settings)
    return tenant, user, access, refresh


async def login(
    db: AsyncSession,
    email: str,
    password: str,
    settings: ApiExecuteSettings,
) -> tuple[Usuario, str, str]:
    """Authenticate a user and return tokens."""
    result = await db.execute(
        select(Usuario).where(Usuario.email == email, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise NotFoundError("Usuario", "invalid credentials")

    access = create_access_token(
        str(user.id), str(user.tenant_id), user.role, user.email, settings,
        sucursal_id=str(user.sucursal_id) if user.sucursal_id else None,
    )
    refresh = create_refresh_token(str(user.id), str(user.tenant_id), settings)
    return user, access, refresh


async def _fetch_google_certs() -> dict[str, str]:
    """Fetch Google public certificates for Firebase ID token verification."""
    global _cached_certs
    if _cached_certs:
        return _cached_certs
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_CERTS_URL, timeout=10.0)
        resp.raise_for_status()
        _cached_certs = resp.json()
        return _cached_certs


async def _resolve_firebase_cert(kid: str) -> str:
    """Fetch the PEM certificate for the given key ID, retrying on cache miss."""
    global _cached_certs
    certs = await _fetch_google_certs()
    cert_pem = certs.get(kid)
    if cert_pem:
        return cert_pem
    _cached_certs = None
    certs = await _fetch_google_certs()
    cert_pem = certs.get(kid)
    if not cert_pem:
        raise ValueError("Token signed with unknown key")
    return cert_pem


def _decode_firebase_claims(token: str, public_key) -> dict:
    """Verify and decode Firebase token claims."""
    try:
        return pyjwt.decode(
            token, public_key, algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}",
        )
    except pyjwt.ExpiredSignatureError:
        raise ValueError("Firebase token expired")
    except pyjwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid Firebase token: {exc}") from exc


async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return its claims.

    Checks signature against Google's public keys, validates iss/aud/exp.
    """
    try:
        header = pyjwt.get_unverified_header(token)
    except pyjwt.exceptions.DecodeError as exc:
        raise ValueError(f"Invalid token format: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        raise ValueError("Token missing kid header")

    cert_pem = await _resolve_firebase_cert(kid)
    cert = load_pem_x509_certificate(cert_pem.encode("utf-8"))
    return _decode_firebase_claims(token, cert.public_key())


async def firebase_login(
    db: AsyncSession,
    firebase_token: str,
    settings: ApiExecuteSettings,
) -> tuple[Usuario, str, str]:
    """Verify Firebase ID token, look up user, and issue backend JWT pair."""
    claims = await verify_firebase_token(firebase_token)
    email = claims.get("email")
    if not email:
        raise NotFoundError("Usuario", "Firebase token missing email claim")

    result = await db.execute(
        select(Usuario).where(Usuario.email == email, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", f"No active user with email {email}")

    access = create_access_token(
        str(user.id), str(user.tenant_id), user.role, user.email, settings,
        sucursal_id=str(user.sucursal_id) if user.sucursal_id else None,
    )
    refresh = create_refresh_token(str(user.id), str(user.tenant_id), settings)
    return user, access, refresh


# ── Password reset (self-service) ────────────────────────────────────────────


async def create_password_reset_token(
    db: AsyncSession, email: str
) -> tuple[Usuario, str] | None:
    """Generate a password reset token. Returns None if user not found (no leak)."""
    result = await db.execute(
        select(Usuario).where(Usuario.email == email, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Invalidate previous tokens for this user
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
        .values(used=True)
    )

    token = secrets.token_urlsafe(48)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset_token)
    await db.flush()
    return user, token


async def reset_password_with_token(
    db: AsyncSession, token: str, new_password: str, settings: ApiExecuteSettings
) -> None:
    """Consume a reset token and set the new password."""
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.used.is_(False),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise NotFoundError("Token", "Token inválido o ya utilizado")

    if reset.expires_at < datetime.now(timezone.utc):
        reset.used = True
        await db.flush()
        raise NotFoundError("Token", "Token expirado")

    reset.used = True

    user_result = await db.execute(
        select(Usuario).where(Usuario.id == reset.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "Usuario no encontrado")

    user.hashed_password = hash_password(new_password, settings.BCRYPT_ROUNDS)
    await db.flush()


# ── Change password (logged-in user) ─────────────────────────────────────────


async def change_password(
    db: AsyncSession,
    user_id: uuid.UUID,
    current_password: str,
    new_password: str,
    settings: ApiExecuteSettings,
) -> None:
    """Change password for the currently logged-in user."""
    result = await db.execute(
        select(Usuario).where(Usuario.id == user_id, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "Usuario no encontrado")

    if not verify_password(current_password, user.hashed_password):
        raise ConflictError("La contraseña actual es incorrecta")

    user.hashed_password = hash_password(new_password, settings.BCRYPT_ROUNDS)
    await db.flush()


# ── Email verification ───────────────────────────────────────────────────────


async def create_email_verification_token(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Generate a 6-digit verification code and store it on the user."""
    result = await db.execute(
        select(Usuario).where(Usuario.id == user_id, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or user.email_verified:
        return None

    code = f"{secrets.randbelow(900000) + 100000}"  # 6-digit numeric code
    token = secrets.token_urlsafe(32)
    # Store the token (used for link-based verification)
    user.email_verification_token = token  # type: ignore[attr-defined]
    user.email_verification_expires = datetime.now(timezone.utc) + timedelta(  # type: ignore[attr-defined]
        minutes=VERIFY_TOKEN_TTL_MINUTES
    )
    await db.flush()
    return f"{code}:{token}"


async def verify_email_with_token(db: AsyncSession, token: str) -> None:
    """Verify user email via token."""
    result = await db.execute(
        select(Usuario).where(
            Usuario.email_verification_token == token,  # type: ignore[attr-defined]
            Usuario.activo.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Token", "Token de verificación inválido")

    if user.email_verification_expires < datetime.now(timezone.utc):  # type: ignore[attr-defined]
        raise NotFoundError("Token", "Token de verificación expirado")

    user.email_verified = True
    user.email_verification_token = None  # type: ignore[attr-defined]
    user.email_verification_expires = None  # type: ignore[attr-defined]
    await db.flush()


# ── Profile update ───────────────────────────────────────────────────────────


async def update_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    nombre: str | None = None,
    apellido: str | None = None,
) -> Usuario:
    """Update the logged-in user's profile fields."""
    result = await db.execute(
        select(Usuario).where(Usuario.id == user_id, Usuario.activo.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", "Usuario no encontrado")

    if nombre is not None:
        user.nombre = nombre
    if apellido is not None:
        user.apellido = apellido
    await db.flush()
    return user
