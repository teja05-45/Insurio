"""Password hashing and JWT helpers.

Passwords use Argon2id via pwdlib. Access tokens are short-lived JWTs; refresh
tokens are opaque random strings whose SHA-256 digest is stored server-side so
they can be revoked and rotated.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.errors import AppError

_password_hash = PasswordHash.recommended()

TOKEN_TYPE_ACCESS = "access"


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _password_hash.verify(password, hashed)
    except Exception:
        return False


def create_access_token(
    subject: str,
    settings: Settings,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "typ": TOKEN_TYPE_ACCESS,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            "Your session has expired. Please sign in again.",
            code="token_expired",
            status_code=401,
        ) from exc
    except jwt.PyJWTError as exc:
        raise AppError("Invalid authentication token.", code="invalid_token", status_code=401) from exc

    if payload.get("typ") != TOKEN_TYPE_ACCESS or not payload.get("sub"):
        raise AppError("Invalid authentication token.", code="invalid_token", status_code=401)
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_reset_token() -> str:
    return secrets.token_urlsafe(40)
