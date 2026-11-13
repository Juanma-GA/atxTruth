"""Password hashing, temporary passwords, RS256 access tokens and refresh tokens."""

import hashlib
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

JWT_ALGORITHM = "RS256"
# bcrypt only looks at the first 72 bytes; longer passwords are rejected instead of silently
# truncated (two passwords sharing a 72-byte prefix would otherwise hash the same).
BCRYPT_MAX_PASSWORD_BYTES = 72
TEMPORARY_PASSWORD_LENGTH = 16
_TEMPORARY_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*"


def generate_temporary_password() -> str:
    """Cryptographically random one-time password, shown to the admin exactly once."""
    while True:
        candidate = "".join(secrets.choice(_TEMPORARY_PASSWORD_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH))
        if any(c.isdigit() for c in candidate) and any(c.isalpha() for c in candidate):
            return candidate


def password_fits_bcrypt(password: str) -> bool:
    return len(password.encode("utf-8")) <= BCRYPT_MAX_PASSWORD_BYTES


def hash_password(password: str) -> str:
    if not password_fits_bcrypt(password):
        raise ValueError("password_too_long")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None or not password_fits_bcrypt(password):
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))


# A hash used to spend the same bcrypt time when the email is unknown (no user enumeration by timing).
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"atxtruth-dummy-password", bcrypt.gensalt()).decode("ascii")


@lru_cache
def _private_key() -> str:
    return get_settings().jwt_private_key_path.read_text(encoding="utf-8")


@lru_cache
def _public_key() -> str:
    return get_settings().jwt_public_key_path.read_text(encoding="utf-8")


def keys_available() -> bool:
    settings = get_settings()
    return settings.jwt_private_key_path.is_file() and settings.jwt_public_key_path.is_file()


def create_access_token(user_id: uuid.UUID) -> str:
    """RS256 access token; `sub` is the only identity claim the app trusts."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().access_token_minutes),
    }
    return jwt.encode(payload, _private_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise jwt.PyJWTError on any invalid token (expired, bad signature, malformed)."""
    claims: dict[str, Any] = jwt.decode(
        token, _public_key(), algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp", "iat"]}
    )
    if claims.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return claims


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw token for the cookie, sha256 hash to store). The raw value is never stored."""
    raw = secrets.token_urlsafe(64)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
