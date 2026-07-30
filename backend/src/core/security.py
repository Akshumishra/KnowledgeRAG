from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from src.core.config import settings


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(UTC)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises jose.JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def is_token_valid(token: str, token_type: str = "access") -> dict | None:
    """Return decoded payload if valid, else None."""
    try:
        payload = decode_token(token)
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt a plaintext API key using Fernet. Returns a base64 token string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(token: str) -> str:
    """Decrypt a Fernet-encrypted API key token. Returns plaintext."""
    return _get_fernet().decrypt(token.encode()).decode()
