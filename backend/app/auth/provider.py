"""Identity entry point. Authorization only ever sees a `CurrentUser`.

AUTH_MODE=local  → LocalAuthProvider: our own RS256 access token (login with email + password).
AUTH_MODE=oidc   → to be implemented by IT (see docs/sso-para-it.md). Nothing else in the app has
                   to change: routes depend on `CurrentUser`, never on how it was obtained.
"""

import uuid
from abc import ABC, abstractmethod

import jwt
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.roles import Role
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.models import User
from app.repositories import users as users_repo


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def to_current_user(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        roles=frozenset({Role(user.role)}),
        must_change_password=user.must_change_password,
    )


class AuthProvider(ABC):
    name: str

    @abstractmethod
    async def resolve(self, request: Request, db: AsyncSession) -> CurrentUser | None:
        """Return the authenticated user for this request, or None when there is none."""


class LocalAuthProvider(AuthProvider):
    name = "local"

    async def resolve(self, request: Request, db: AsyncSession) -> CurrentUser | None:
        token = bearer_token(request)
        if token is None:
            return None
        try:
            claims = decode_access_token(token)
            user_id = uuid.UUID(str(claims["sub"]))
        except (jwt.PyJWTError, ValueError):
            return None
        user = await users_repo.get_active_by_id(db, user_id)
        return to_current_user(user) if user is not None else None


class AuthModeNotImplementedError(RuntimeError):
    pass


def build_auth_provider() -> AuthProvider:
    mode = get_settings().auth_mode
    if mode == "local":
        return LocalAuthProvider()
    # HR7: no silent fallback to local login. Fail at startup and point to the handover doc.
    raise AuthModeNotImplementedError(
        f"AUTH_MODE={mode} is not implemented yet; see docs/sso-para-it.md for what IT has to add."
    )
