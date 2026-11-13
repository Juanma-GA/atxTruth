"""FastAPI dependencies for authentication and server-side role checks."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.provider import AuthProvider
from app.auth.roles import Role
from app.core.errors import AppError
from app.db.base import get_db


def get_auth_provider(request: Request) -> AuthProvider:
    provider: AuthProvider = request.app.state.auth_provider
    return provider


async def get_current_user_allow_pending(
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider: AuthProvider = Depends(get_auth_provider),
) -> CurrentUser:
    """Authenticated user, even if they still have to change a temporary password."""
    user = await provider.resolve(request, db)
    if user is None:
        raise AppError(401, "auth.not_authenticated")
    return user


async def get_current_user(user: CurrentUser = Depends(get_current_user_allow_pending)) -> CurrentUser:
    """Authenticated user who has no pending password change (enforced server-side)."""
    if user.must_change_password:
        raise AppError(403, "auth.password_change_required")
    return user


def require_roles(*roles: Role) -> Callable[..., Awaitable[CurrentUser]]:
    """Dependency that rejects with 403 unless the user has one of `roles`.

    The role comes from the server (database or validated IdP token), never from the client.
    """

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_any(*roles):
            raise AppError(403, "auth.forbidden")
        return user

    return dependency


require_admin = require_roles(Role.ADMIN)
require_editor = require_roles(Role.ADMIN, Role.EDITOR)
