"""JWT authentication helpers for user and inter-service requests."""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status

from shared.models.enums import UserRole

_SERVICE_TOKEN_TYPE = "service"
_ACCESS_TOKEN_TYPES = {None, "access", "user"}


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
    audience: str | None = None,
) -> dict[str, Any]:
    """Decode and validate a signed JWT."""
    options = {"verify_aud": audience is not None}
    kwargs = {"algorithms": [algorithm], "options": options}
    if audience is not None:
        kwargs["audience"] = audience
    try:
        return jwt.decode(token, secret_key, **kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise _unauthorized("Invalid token audience") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid token") from exc


def create_service_token(
    *,
    service_name: str,
    audience: str,
    tenant_id: UUID,
    signing_key: str | None = None,
    secret_key: str | None = None,
    algorithm: str = "HS256",
    scopes: Iterable[str],
    expires_in_seconds: int = 300,
) -> str:
    """Create a short-lived service JWT with explicit audience and scopes."""
    issued_at = int(time.time())
    payload = {
        "iss": service_name,
        "sub": service_name,
        "aud": audience,
        "tenant_id": str(tenant_id),
        "type": _SERVICE_TOKEN_TYPE,
        "role": UserRole.ADMIN.value,
        "scopes": sorted({scope for scope in scopes if scope}),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + expires_in_seconds,
    }
    return jwt.encode(payload, _resolve_service_signing_key(signing_key, secret_key), algorithm=algorithm)


def build_service_auth_headers(
    *,
    service_name: str,
    audience: str,
    tenant_id: UUID,
    signing_key: str | None = None,
    secret_key: str | None = None,
    algorithm: str = "HS256",
    scopes: Iterable[str],
    expires_in_seconds: int = 300,
) -> dict[str, str]:
    """Build Authorization and tenant headers for an internal service call."""
    token = create_service_token(
        service_name=service_name,
        audience=audience,
        tenant_id=tenant_id,
        signing_key=signing_key,
        secret_key=secret_key,
        algorithm=algorithm,
        scopes=scopes,
        expires_in_seconds=expires_in_seconds,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }


def resolve_request_auth_context(request: Request) -> dict[str, Any] | None:
    """Resolve the authenticated actor from the request headers, if present."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return None
    if not auth_header.startswith("Bearer "):
        raise _unauthorized("Invalid authorization scheme")

    token = auth_header[7:].strip()
    if not token:
        raise _unauthorized("Missing bearer token")

    requested_tenant = request.headers.get("X-Tenant-ID")
    requested_tenant_id = _parse_optional_uuid(requested_tenant, "X-Tenant-ID")
    unverified = _peek_token_claims(token)
    token_type = unverified.get("type")

    if token_type == _SERVICE_TOKEN_TYPE:
        context = _decode_service_context(request, token)
    else:
        context = _decode_user_context(request, token)

    if requested_tenant_id is not None and requested_tenant_id != context["tenant_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Tenant-ID does not match authenticated tenant",
        )

    return context


def get_current_actor(request: Request) -> dict[str, Any]:
    """Return the authenticated user or service actor for this request."""
    error = getattr(request.state, "auth_error", None)
    if error is not None:
        raise error
    actor = getattr(request.state, "auth_context", None)
    if actor is None:
        raise _unauthorized("Not authenticated")
    return actor


def get_current_user(request: Request) -> dict[str, Any]:
    """Return the authenticated human user for this request."""
    actor = get_current_actor(request)
    if actor["type"] != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service tokens are not allowed on this endpoint",
        )
    return actor


def get_current_service(request: Request) -> dict[str, Any]:
    """Return the authenticated calling service for this request."""
    actor = get_current_actor(request)
    if actor["type"] != _SERVICE_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User tokens are not allowed on this endpoint",
        )
    return actor


def require_role(*roles: UserRole):
    """Dependency factory that enforces role-based access for user JWTs."""

    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user['role']} not authorized",
            )
        return current_user

    return checker


def require_service(*scopes: str, callers: Iterable[str] | None = None):
    """Dependency factory that enforces service JWT scopes and allowed callers."""
    allowed_callers = set(callers or [])
    required_scopes = {scope for scope in scopes if scope}

    def checker(current_service: dict = Depends(get_current_service)) -> dict:
        _validate_service_access(current_service, required_scopes, allowed_callers)
        return current_service

    return checker


def require_user_or_service(
    *roles: UserRole,
    service_scopes: Iterable[str],
    service_callers: Iterable[str] | None = None,
):
    """Allow either a user role or an internal service token with explicit scopes."""
    required_scopes = {scope for scope in service_scopes if scope}
    allowed_callers = set(service_callers or [])

    def checker(current_actor: dict = Depends(get_current_actor)) -> dict:
        if current_actor["type"] == "user":
            if roles and current_actor["role"] not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {current_actor['role']} not authorized",
                )
            return current_actor

        if not required_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service tokens are not allowed on this endpoint",
            )
        _validate_service_access(current_actor, required_scopes, allowed_callers)
        return current_actor

    return checker


def _decode_user_context(request: Request, token: str) -> dict[str, Any]:
    payload = decode_token(
        token,
        request.app.state.jwt_secret_key,
        getattr(request.app.state, "jwt_algorithm", "HS256"),
    )
    token_type = payload.get("type")
    if token_type not in _ACCESS_TOKEN_TYPES:
        raise _unauthorized("Unsupported token type for user authentication")
    for field in ("sub", "tenant_id", "role"):
        if field not in payload:
            raise _unauthorized(f"Missing claim: {field}")
    return {
        "type": "user",
        "user_id": _parse_required_uuid(payload.get("sub"), "sub"),
        "tenant_id": _parse_required_uuid(payload.get("tenant_id"), "tenant_id"),
        "role": UserRole(payload["role"]),
        "email": payload.get("email"),
        "sucursal_id": _parse_optional_uuid(payload.get("sucursal_id"), "sucursal_id"),
        "service_name": None,
        "scopes": tuple(),
        "claims": payload,
    }


def _decode_service_context(request: Request, token: str) -> dict[str, Any]:
    unverified = _peek_token_claims(token)
    issuer = _extract_service_identity(unverified)
    payload = decode_token(
        token,
        _trusted_service_key(request, issuer),
        getattr(request.app.state, "jwt_algorithm", "HS256"),
        audience=request.app.state.service_name,
    )
    if payload.get("type") != _SERVICE_TOKEN_TYPE:
        raise _unauthorized("Unsupported token type for service authentication")
    verified_issuer = _extract_service_identity(payload)
    if verified_issuer != issuer:
        raise _unauthorized("Invalid service identity")
    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list) or any(not isinstance(item, str) for item in scopes):
        raise _unauthorized("Invalid service scopes")
    role_value = payload.get("role")
    role = UserRole(role_value) if role_value in {member.value for member in UserRole} else UserRole.ADMIN
    return {
        "type": _SERVICE_TOKEN_TYPE,
        "user_id": None,
        "tenant_id": _parse_required_uuid(payload.get("tenant_id"), "tenant_id"),
        "role": role,
        "email": None,
        "service_name": verified_issuer,
        "scopes": tuple(sorted(set(scopes))),
        "claims": payload,
    }


def _peek_token_claims(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid token") from exc
    if not isinstance(payload, dict):
        raise _unauthorized("Invalid token")
    return payload


def _validate_service_access(
    service_actor: dict[str, Any],
    required_scopes: set[str],
    allowed_callers: set[str],
) -> None:
    if allowed_callers and service_actor["service_name"] not in allowed_callers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service {service_actor['service_name']} not authorized",
        )
    missing_scopes = sorted(required_scopes.difference(service_actor["scopes"]))
    if missing_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing service scope: {missing_scopes[0]}",
        )


def _resolve_service_signing_key(
    signing_key: str | None,
    secret_key: str | None,
) -> str:
    key = signing_key or secret_key
    if key is None or not key.strip():
        raise ValueError("A signing key is required for internal service JWTs")
    return key


def _extract_service_identity(payload: Mapping[str, Any]) -> str:
    issuer = payload.get("iss")
    subject = payload.get("sub")
    if not isinstance(issuer, str) or not issuer.strip():
        raise _unauthorized("Missing claim: iss")
    if not isinstance(subject, str) or not subject.strip():
        raise _unauthorized("Missing claim: sub")
    issuer = issuer.strip()
    subject = subject.strip()
    if issuer != subject:
        raise _unauthorized("Service token identity mismatch")
    return issuer


def _trusted_service_key(request: Request, issuer: str) -> str:
    trusted_keys = getattr(request.app.state, "internal_service_trusted_keys", None)
    if not isinstance(trusted_keys, dict):
        raise RuntimeError("internal_service_trusted_keys is not configured")
    key = trusted_keys.get(issuer)
    if not isinstance(key, str) or not key.strip():
        raise _unauthorized("Untrusted service issuer")
    return key


def _parse_optional_uuid(value: str | None, field_name: str) -> UUID | None:
    if value is None or not str(value).strip():
        return None
    return _parse_required_uuid(value, field_name)


def _parse_required_uuid(value: Any, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise _unauthorized(f"Invalid claim: {field_name}") from exc


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
