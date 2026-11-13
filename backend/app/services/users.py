"""User administration (local mode only): create, change role, deactivate, restore, delete."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.roles import Role
from app.core.errors import AppError
from app.core.security import generate_temporary_password, hash_password
from app.models import User
from app.repositories import refresh_tokens as tokens_repo
from app.repositories import users as users_repo
from app.schemas.users import UserCreate, UserUpdate
from app.services import audit


def snapshot(user: User) -> dict[str, Any]:
    return {
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "preferred_language": user.preferred_language,
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
    }


async def _get(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await users_repo.get_by_id(db, user_id)
    if user is None:
        raise AppError(404, "users.not_found")
    return user


async def _ensure_not_last_admin(db: AsyncSession, user: User) -> None:
    if user.role == Role.ADMIN and user.deleted_at is None and await users_repo.count_active_admins(db) <= 1:
        raise AppError(409, "users.last_admin")


def _audit(
    db: AsyncSession,
    actor: CurrentUser,
    action: str,
    user: User,
    request: Request | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    audit.record(
        db,
        actor=actor,
        action=action,
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
        before=before,
        after=after,
        request=request,
    )


async def list_users(db: AsyncSession, *, include_deleted: bool) -> Sequence[User]:
    return await users_repo.list_users(db, include_deleted=include_deleted)


async def create_user(
    db: AsyncSession, body: UserCreate, *, actor: CurrentUser, request: Request | None
) -> tuple[User, str]:
    email = body.email.lower()
    if await users_repo.get_by_email(db, email) is not None:
        raise AppError(409, "users.email_taken")
    temporary = generate_temporary_password()
    user = users_repo.add(
        db,
        User(
            email=email,
            display_name=body.display_name,
            role=body.role,
            preferred_language=body.preferred_language,
            password_hash=hash_password(temporary),
            must_change_password=True,
        ),
    )
    await db.flush()
    _audit(db, actor, "user.created", user, request, after=snapshot(user))
    await db.commit()
    await db.refresh(user)
    return user, temporary


async def update_user(
    db: AsyncSession, user_id: uuid.UUID, body: UserUpdate, *, actor: CurrentUser, request: Request | None
) -> User:
    user = await _get(db, user_id)
    before = snapshot(user)
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    if "role" in changes and changes["role"] != user.role:
        if user.id == actor.id:
            raise AppError(409, "users.cannot_change_own_role")
        if user.role == Role.ADMIN:
            await _ensure_not_last_admin(db, user)
    for field, value in changes.items():
        setattr(user, field, value)
    if snapshot(user) != before:
        _audit(db, actor, "user.updated", user, request, before=before, after=snapshot(user))
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID, *, actor: CurrentUser, request: Request | None) -> User:
    user = await _get(db, user_id)
    if user.id == actor.id:
        raise AppError(409, "users.cannot_deactivate_self")
    if user.deleted_at is not None:
        return user
    await _ensure_not_last_admin(db, user)
    before = snapshot(user)
    now = datetime.now(UTC)
    users_repo.mark_deleted(user, by=actor.id, at=now)
    await tokens_repo.revoke_all(db, user.id, at=now)
    _audit(db, actor, "user.deactivated", user, request, before=before, after=snapshot(user))
    await db.commit()
    await db.refresh(user)
    return user


async def restore_user(db: AsyncSession, user_id: uuid.UUID, *, actor: CurrentUser, request: Request | None) -> User:
    user = await _get(db, user_id)
    if user.deleted_at is None:
        return user
    before = snapshot(user)
    user.deleted_at = None
    user.deleted_by = None
    _audit(db, actor, "user.restored", user, request, before=before, after=snapshot(user))
    await db.commit()
    await db.refresh(user)
    return user


async def reset_password(
    db: AsyncSession, user_id: uuid.UUID, *, actor: CurrentUser, request: Request | None
) -> tuple[User, str]:
    user = await _get(db, user_id)
    if user.deleted_at is not None:
        raise AppError(409, "users.inactive")
    temporary = generate_temporary_password()
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    await tokens_repo.revoke_all(db, user.id, at=datetime.now(UTC))
    _audit(db, actor, "user.password_reset", user, request)
    await db.commit()
    await db.refresh(user)
    return user, temporary


async def delete_permanently(
    db: AsyncSession, user_id: uuid.UUID, confirm_email: str, *, actor: CurrentUser, request: Request | None
) -> None:
    """Hard delete (HR9): only a deactivated user, only with the email typed as confirmation."""
    user = await _get(db, user_id)
    if user.deleted_at is None:
        raise AppError(409, "users.must_deactivate_first")
    if confirm_email.lower() != user.email:
        raise AppError(422, "users.confirmation_mismatch")
    _audit(db, actor, "user.deleted_permanently", user, request, before=snapshot(user))
    await users_repo.delete(db, user)
    await db.commit()
