"""Security helpers for secret validation and at-rest encryption."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

MIN_SECRET_LENGTH_BYTES = 32
ENCRYPTED_SECRET_PREFIX = "enc:v1:"


def validate_secret_length(secret: str, field_name: str) -> str:
    """Reject weak shared secrets used for JWT/HMAC or internal service auth."""
    value = secret.strip()
    if len(value.encode("utf-8")) < MIN_SECRET_LENGTH_BYTES:
        raise ValueError(
            f"{field_name} must be at least {MIN_SECRET_LENGTH_BYTES} bytes for HS256"
        )
    return value


def mask_secret(secret: str) -> str:
    """Return a stable masked representation without exposing the full value."""
    if len(secret) <= 8:
        return "****"
    if len(secret) <= 16:
        return f"{secret[:4]}****{secret[-4:]}"
    return f"{secret[:8]}****{secret[-4:]}"


def is_encrypted_secret(value: str) -> bool:
    """Detect the application-level ciphertext format."""
    return value.startswith(ENCRYPTED_SECRET_PREFIX)


def encrypt_secret(plaintext: str, master_key: str) -> str:
    """Encrypt a plaintext secret with a derived Fernet key."""
    if is_encrypted_secret(plaintext):
        return plaintext
    token = Fernet(_derive_fernet_key(master_key)).encrypt(plaintext.encode("utf-8"))
    return f"{ENCRYPTED_SECRET_PREFIX}{token.decode('utf-8')}"


def decrypt_secret(ciphertext: str, master_key: str) -> str:
    """Decrypt a stored secret or return legacy plaintext as-is."""
    if not is_encrypted_secret(ciphertext):
        return ciphertext
    raw_token = ciphertext[len(ENCRYPTED_SECRET_PREFIX) :].encode("utf-8")
    try:
        return Fernet(_derive_fernet_key(master_key)).decrypt(raw_token).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Encrypted secret cannot be decrypted with the configured master key") from exc


def _derive_fernet_key(master_key: str) -> bytes:
    digest = hashlib.sha256(validate_secret_length(master_key, "LLM_PROVIDER_KEY_MASTER_KEY").encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)
