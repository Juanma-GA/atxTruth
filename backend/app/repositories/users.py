"""Data access for users. Only this module queries the `users` table."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_active_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, *, include_deleted: bool) -> Sequence[User]:
    query = select(User).order_by(User.email)
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))
    result = await db.execute(query)
    return result.scalars().all()


async def count_active_admins(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(User.role == "admin", User.deleted_at.is_(None))
    )
    return int(result.scalar_one())


def add(db: AsyncSession, user: User) -> User:
    db.add(user)
    return user


async def delete(db: AsyncSession, user: User) -> None:
    await db.delete(user)


def mark_deleted(user: User, *, by: uuid.UUID, at: datetime) -> None:
    user.deleted_at = at
    user.deleted_by = by
