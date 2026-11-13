"""Data access for refresh sessions."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


def add(db: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> None:
    db.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))


async def get_by_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def revoke_all(db: AsyncSession, user_id: uuid.UUID, *, at: datetime, keep_hash: str | None = None) -> None:
    """Revoke every active session of the user, except `keep_hash` (the caller's own session)."""
    query = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    if keep_hash is not None:
        query = query.where(RefreshToken.token_hash != keep_hash)
    await db.execute(query.values(revoked_at=at))
