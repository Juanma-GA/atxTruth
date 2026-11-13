"""User administration routes (admin only; mounted only with AUTH_MODE=local)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import require_admin
from app.db.base import get_db
from app.schemas.users import HardDeleteRequest, UserCreate, UserOut, UserUpdate, UserWithTemporaryPassword
from app.services import users as users_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    include_deleted: bool = Query(default=False),
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    users = await users_service.list_users(db, include_deleted=include_deleted)
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserWithTemporaryPassword, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserWithTemporaryPassword:
    user, temporary = await users_service.create_user(db, body, actor=admin, request=request)
    return UserWithTemporaryPassword(user=UserOut.model_validate(user), temporary_password=temporary)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return UserOut.model_validate(await users_service.update_user(db, user_id, body, actor=admin, request=request))


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return UserOut.model_validate(await users_service.deactivate_user(db, user_id, actor=admin, request=request))


@router.post("/{user_id}/restore", response_model=UserOut)
async def restore_user(
    user_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return UserOut.model_validate(await users_service.restore_user(db, user_id, actor=admin, request=request))


@router.post("/{user_id}/reset-password", response_model=UserWithTemporaryPassword)
async def reset_password(
    user_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserWithTemporaryPassword:
    user, temporary = await users_service.reset_password(db, user_id, actor=admin, request=request)
    return UserWithTemporaryPassword(user=UserOut.model_validate(user), temporary_password=temporary)


@router.post("/{user_id}/delete-permanently", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permanently(
    user_id: uuid.UUID,
    body: HardDeleteRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await users_service.delete_permanently(db, user_id, body.confirm_email, actor=admin, request=request)
