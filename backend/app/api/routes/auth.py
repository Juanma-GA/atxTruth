"""Authentication routes.

`local_router` (login / refresh / logout / change-password) is only mounted with AUTH_MODE=local.
`router` (/me) works with any AuthProvider.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import get_current_user_allow_pending
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.base import get_db
from app.schemas.auth import ChangePasswordRequest, LoginRequest, MeOut, MeUpdate, TokenResponse
from app.services import auth as auth_service

REFRESH_COOKIE = "atx_refresh"
# Only the auth endpoints that read it receive the cookie.
REFRESH_COOKIE_PATH = "/api/auth"

router = APIRouter(prefix="/api/auth", tags=["auth"])
local_router = APIRouter(prefix="/api/auth", tags=["auth"])


def _check_origin(request: Request) -> None:
    """CSRF defence for cookie-authenticated endpoints (on top of SameSite=Strict)."""
    origin = request.headers.get("Origin")
    if origin is not None and origin not in get_settings().cors_origins:
        raise AppError(403, "auth.origin_not_allowed")


def _set_cookie(response: Response, session: auth_service.IssuedSession) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        session.refresh_token,
        max_age=session.max_age_seconds,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


@local_router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    _check_origin(request)
    session = await auth_service.login(db, body.email, body.password, request)
    _set_cookie(response, session)
    return TokenResponse(access_token=session.access_token)


@local_router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _check_origin(request)
    session = await auth_service.refresh(db, request.cookies.get(REFRESH_COOKIE), request)
    _set_cookie(response, session)
    return TokenResponse(access_token=session.access_token)


@local_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    _check_origin(request)
    await auth_service.logout(db, request.cookies.get(REFRESH_COOKIE), request)
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=get_settings().cookie_secure, httponly=True, samesite="strict"
    )


@local_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user_allow_pending),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.change_password(
        db, user, body.current_password, body.new_password, request.cookies.get(REFRESH_COOKIE), request
    )


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser = Depends(get_current_user_allow_pending), db: AsyncSession = Depends(get_db)) -> MeOut:
    return MeOut.model_validate(await auth_service.get_me(db, user))


@router.patch("/me", response_model=MeOut)
async def update_me(
    body: MeUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user_allow_pending),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    return MeOut.model_validate(await auth_service.update_me(db, user, body, request))
