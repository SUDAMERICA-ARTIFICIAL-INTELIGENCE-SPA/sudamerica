"""Helpers to validate per-issuer internal service JWT configuration."""

from __future__ import annotations

from collections.abc import Mapping

from shared.utils.security import validate_secret_length

SERVICE_ISSUERS = (
    "api_execute",
    "ai_dialer",
    "callback_manual",
    "tasks",
    "canales_service",
    "open_agent",
)


def _resolve_issuer_key(
    issuer: str,
    service_name: str,
    signing_key: str,
    trusted_keys: Mapping[str, str | None],
) -> str | None:
    """Resolve and validate a single issuer's key. Returns None to skip."""
    raw_key = signing_key if issuer == service_name else (trusted_keys.get(issuer) or "")
    field_name = f"{issuer.upper()}_INTERNAL_SERVICE_SECRET_KEY"
    if not raw_key or not raw_key.strip():
        if issuer != service_name and issuer not in trusted_keys:
            return None
        raise ValueError(f"{field_name} must be configured")
    return validate_secret_length(raw_key, field_name)


def _check_key_uniqueness(resolved: dict[str, str]) -> None:
    """Raise if any two issuers share the same key."""
    seen: dict[str, str] = {}
    for issuer, key in resolved.items():
        duplicate = seen.get(key)
        if duplicate is not None:
            raise ValueError(
                "Internal service JWT keys must be unique per issuer: "
                f"{duplicate} and {issuer} share the same key"
            )
        seen[key] = issuer


def build_internal_service_trust_map(
    *,
    service_name: str,
    signing_key: str,
    trusted_keys: Mapping[str, str | None],
) -> dict[str, str]:
    """Return a validated issuer->verification-key map for service JWTs."""
    if service_name not in SERVICE_ISSUERS:
        raise ValueError(f"Unsupported internal service issuer: {service_name}")

    resolved: dict[str, str] = {}
    for issuer in SERVICE_ISSUERS:
        key = _resolve_issuer_key(issuer, service_name, signing_key, trusted_keys)
        if key is not None:
            resolved[issuer] = key

    _check_key_uniqueness(resolved)
    return resolved
