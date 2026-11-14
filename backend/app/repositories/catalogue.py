"""Data access for the catalogue taxonomy. Only this module queries those tables."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdjacentActivity, Block, CatalogueEdition, Family, Service, Solution

CatalogueModel = type[Block] | type[Family] | type[Service] | type[Solution] | type[AdjacentActivity]


async def editions(db: AsyncSession) -> Sequence[CatalogueEdition]:
    query = select(CatalogueEdition).where(CatalogueEdition.deleted_at.is_(None)).order_by(CatalogueEdition.code)
    return (await db.execute(query)).scalars().all()


async def edition_by_code(db: AsyncSession, code: str) -> CatalogueEdition | None:
    query = select(CatalogueEdition).where(CatalogueEdition.code == code, CatalogueEdition.deleted_at.is_(None))
    return (await db.execute(query)).scalar_one_or_none()


async def all_of(
    db: AsyncSession, model: CatalogueModel, edition_id: uuid.UUID, *, include_deleted: bool = False
) -> Sequence[Any]:
    query = select(model).where(model.edition_id == edition_id)
    if not include_deleted:
        query = query.where(model.deleted_at.is_(None))
    return (await db.execute(query)).scalars().all()


async def get(db: AsyncSession, model: CatalogueModel, entity_id: uuid.UUID) -> Any:
    return await db.get(model, entity_id)


async def by_code(db: AsyncSession, model: CatalogueModel, edition_id: uuid.UUID, code: str) -> Any:
    query = select(model).where(model.edition_id == edition_id, model.code == code, model.deleted_at.is_(None))
    return (await db.execute(query)).scalar_one_or_none()


async def active_children(
    db: AsyncSession, model: type[Family] | type[Service], parent_attr: str, parent_id: uuid.UUID
) -> list[str]:
    column = getattr(model, parent_attr)
    query = select(model.code).where(column == parent_id, model.deleted_at.is_(None))
    return [str(code) for code in (await db.execute(query)).scalars().all()]


def add(db: AsyncSession, entity: Any) -> None:
    db.add(entity)
