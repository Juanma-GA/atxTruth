"""Data access for functional settings."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting


async def list_all(db: AsyncSession) -> Sequence[AppSetting]:
    result = await db.execute(select(AppSetting).order_by(AppSetting.category, AppSetting.sort_order))
    return result.scalars().all()


async def get(db: AsyncSession, key: str, *, for_update: bool = False) -> AppSetting | None:
    query = select(AppSetting).where(AppSetting.key == key)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def values(db: AsyncSession, keys: Sequence[str]) -> dict[str, object]:
    result = await db.execute(select(AppSetting.key, AppSetting.value).where(AppSetting.key.in_(keys)))
    return {key: value for key, value in result.all()}
