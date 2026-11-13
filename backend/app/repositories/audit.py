"""Data access for the audit trail."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


def add(db: AsyncSession, event: AuditEvent) -> None:
    db.add(event)


async def page(
    db: AsyncSession, *, offset: int, limit: int, action_prefix: str | None
) -> tuple[Sequence[AuditEvent], int]:
    query = select(AuditEvent)
    count_query = select(func.count()).select_from(AuditEvent)
    if action_prefix:
        condition = AuditEvent.action.startswith(action_prefix, autoescape=True)
        query = query.where(condition)
        count_query = count_query.where(condition)
    result = await db.execute(query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id).offset(offset).limit(limit))
    total = (await db.execute(count_query)).scalar_one()
    return result.scalars().all(), int(total)


async def count_since(db: AsyncSession, *, action: str, target_label: str, since: datetime) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.action == action, AuditEvent.target_label == target_label, AuditEvent.occurred_at > since)
    )
    return int(result.scalar_one())


async def latest(db: AsyncSession, *, action: str, target_label: str) -> datetime | None:
    result = await db.execute(
        select(func.max(AuditEvent.occurred_at)).where(
            AuditEvent.action == action, AuditEvent.target_label == target_label
        )
    )
    value: datetime | None = result.scalar_one()
    return value
