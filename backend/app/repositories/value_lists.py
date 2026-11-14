"""Data access for value lists and their items. Only this module queries those tables."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValueList, ValueListItem


async def list_lists(db: AsyncSession, *, include_deleted: bool) -> Sequence[ValueList]:
    query = select(ValueList)
    if not include_deleted:
        query = query.where(ValueList.deleted_at.is_(None))
    return (await db.execute(query)).scalars().all()


async def item_counts(db: AsyncSession) -> dict[uuid.UUID, tuple[int, int]]:
    """list_id → (non-deleted items, active non-deleted items)."""
    rows = await db.execute(
        select(
            ValueListItem.list_id,
            func.count(),
            func.count().filter(ValueListItem.is_active.is_(True)),
        )
        .where(ValueListItem.deleted_at.is_(None))
        .group_by(ValueListItem.list_id)
    )
    return {list_id: (int(total), int(active)) for list_id, total, active in rows.all()}


async def get_list(db: AsyncSession, list_id: uuid.UUID, *, for_update: bool = False) -> ValueList | None:
    query = select(ValueList).where(ValueList.id == list_id)
    if for_update:
        query = query.with_for_update()
    return (await db.execute(query)).scalar_one_or_none()


async def get_list_by_code(db: AsyncSession, code: str) -> ValueList | None:
    query = select(ValueList).where(ValueList.code == code, ValueList.deleted_at.is_(None))
    return (await db.execute(query)).scalar_one_or_none()


async def list_items(db: AsyncSession, list_id: uuid.UUID, *, include_deleted: bool) -> Sequence[ValueListItem]:
    query = select(ValueListItem).where(ValueListItem.list_id == list_id)
    if not include_deleted:
        query = query.where(ValueListItem.deleted_at.is_(None))
    return (await db.execute(query.order_by(ValueListItem.sort_order, ValueListItem.code))).scalars().all()


async def all_items(db: AsyncSession) -> Sequence[ValueListItem]:
    """Every non-deleted item of every non-deleted list."""
    query = (
        select(ValueListItem)
        .join(ValueList, ValueList.id == ValueListItem.list_id)
        .where(ValueListItem.deleted_at.is_(None), ValueList.deleted_at.is_(None))
    )
    return (await db.execute(query)).scalars().all()


async def get_item(db: AsyncSession, item_id: uuid.UUID) -> ValueListItem | None:
    return await db.get(ValueListItem, item_id)


async def get_item_by_code(db: AsyncSession, list_id: uuid.UUID, code: str) -> ValueListItem | None:
    query = select(ValueListItem).where(
        ValueListItem.list_id == list_id, ValueListItem.code == code, ValueListItem.deleted_at.is_(None)
    )
    return (await db.execute(query)).scalar_one_or_none()


async def max_sort_order(db: AsyncSession, list_id: uuid.UUID) -> int:
    value = await db.execute(
        select(func.max(ValueListItem.sort_order)).where(
            ValueListItem.list_id == list_id, ValueListItem.deleted_at.is_(None)
        )
    )
    return int(value.scalar_one() or 0)


def add(db: AsyncSession, entity: ValueList | ValueListItem) -> None:
    db.add(entity)
