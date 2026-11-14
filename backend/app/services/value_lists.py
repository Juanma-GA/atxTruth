"""Value lists: create, edit, reorder, soft delete and restore lists and their items.

Business operations here never commit: the caller (a route, or the Excel import that applies a whole
file in one transaction) does. Every change is recorded through the AuditContext.
"""

import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.codes import SLUG_RE, slugify
from app.core.errors import AppError
from app.models import ValueList, ValueListItem
from app.repositories import value_lists as repo
from app.schemas.translatable import TranslatableText
from app.services.audit import AuditContext

# Where an item may be in use (references from E2 on). Each checker returns how many records use it.
# Deleting an item in use is refused: it must be deactivated instead.
ItemUsageChecker = Callable[[AsyncSession, ValueListItem], Awaitable[int]]
ITEM_USAGE_CHECKERS: list[ItemUsageChecker] = []


async def item_usage(db: AsyncSession, item: ValueListItem) -> int:
    """Single point that says whether an item is used (0 in E1: nothing references items yet)."""
    total = 0
    for checker in ITEM_USAGE_CHECKERS:
        total += await checker(db, item)
    return total


def list_snapshot(value_list: ValueList) -> dict[str, Any]:
    return {
        "code": value_list.code,
        "name": value_list.name.to_db(),
        "description": value_list.description.to_db() if value_list.description else None,
        "is_system": value_list.is_system,
    }


def _check_code(code: str, error: str) -> str:
    if not SLUG_RE.fullmatch(code):
        raise AppError(422, error, {"code": code})
    return code


async def get_list(db: AsyncSession, list_id: uuid.UUID) -> ValueList:
    value_list = await repo.get_list(db, list_id)
    if value_list is None:
        raise AppError(404, "value_lists.not_found")
    return value_list


async def get_item(db: AsyncSession, item_id: uuid.UUID) -> ValueListItem:
    item = await repo.get_item(db, item_id)
    if item is None:
        raise AppError(404, "value_lists.item_not_found")
    return item


async def list_lists(db: AsyncSession, *, include_deleted: bool) -> list[tuple[ValueList, int, int]]:
    lists = await repo.list_lists(db, include_deleted=include_deleted)
    counts = await repo.item_counts(db)
    rows = [(vl, *counts.get(vl.id, (0, 0))) for vl in lists]
    return sorted(rows, key=lambda row: row[0].code)


async def create_list(
    db: AsyncSession,
    ctx: AuditContext,
    *,
    code: str,
    name: TranslatableText,
    description: TranslatableText | None,
    is_system: bool = False,
) -> ValueList:
    _check_code(code, "value_lists.invalid_code")
    if await repo.get_list_by_code(db, code) is not None:
        raise AppError(409, "value_lists.code_taken", {"code": code})
    value_list = ValueList(code=code, name=name, description=description, is_system=is_system)
    repo.add(db, value_list)
    await db.flush()
    ctx.record(
        db,
        action="value_list.created",
        target_type="value_list",
        target_id=str(value_list.id),
        target_label=code,
        after=list_snapshot(value_list),
    )
    return value_list


async def update_list(db: AsyncSession, ctx: AuditContext, value_list: ValueList, changes: dict[str, Any]) -> ValueList:
    if value_list.deleted_at is not None:
        raise AppError(409, "value_lists.deleted")
    before = list_snapshot(value_list)
    if "code" in changes and changes["code"] != value_list.code:
        if value_list.is_system:
            raise AppError(409, "value_lists.system_list", {"code": value_list.code})
        _check_code(changes["code"], "value_lists.invalid_code")
        if await repo.get_list_by_code(db, changes["code"]) is not None:
            raise AppError(409, "value_lists.code_taken", {"code": changes["code"]})
        value_list.code = changes["code"]
    if "name" in changes:
        value_list.name = changes["name"]
    if "description" in changes:
        value_list.description = changes["description"]
    after = list_snapshot(value_list)
    if after != before:
        ctx.record(
            db,
            action="value_list.updated",
            target_type="value_list",
            target_id=str(value_list.id),
            target_label=value_list.code,
            before=before,
            after=after,
        )
    return value_list


async def delete_list(db: AsyncSession, ctx: AuditContext, value_list: ValueList) -> ValueList:
    if value_list.is_system:
        raise AppError(409, "value_lists.system_list", {"code": value_list.code})
    if value_list.deleted_at is not None:
        return value_list
    value_list.deleted_at = datetime.now(UTC)
    value_list.deleted_by = ctx.actor.id if ctx.actor else None
    ctx.record(
        db,
        action="value_list.deleted",
        target_type="value_list",
        target_id=str(value_list.id),
        target_label=value_list.code,
        before=list_snapshot(value_list),
    )
    return value_list


async def restore_list(db: AsyncSession, ctx: AuditContext, value_list: ValueList) -> ValueList:
    if value_list.deleted_at is None:
        return value_list
    if await repo.get_list_by_code(db, value_list.code) is not None:
        raise AppError(409, "value_lists.code_taken", {"code": value_list.code})
    value_list.deleted_at = None
    value_list.deleted_by = None
    ctx.record(
        db,
        action="value_list.restored",
        target_type="value_list",
        target_id=str(value_list.id),
        target_label=value_list.code,
        after=list_snapshot(value_list),
    )
    return value_list


def _item_label(value_list: ValueList, item: ValueListItem) -> str:
    return f"{value_list.code}.{item.code}"


async def create_item(
    db: AsyncSession,
    ctx: AuditContext,
    value_list: ValueList,
    *,
    code: str | None,
    label: TranslatableText,
    description: TranslatableText | None,
    is_active: bool = True,
    sort_order: int | None = None,
) -> ValueListItem:
    if value_list.deleted_at is not None:
        raise AppError(409, "value_lists.deleted")
    code = _check_code(code or slugify(label.en), "value_lists.invalid_item_code")
    if await repo.get_item_by_code(db, value_list.id, code) is not None:
        raise AppError(409, "value_lists.item_code_taken", {"code": code})
    if sort_order is None:
        sort_order = await repo.max_sort_order(db, value_list.id) + 10
    item = ValueListItem(
        list_id=value_list.id,
        code=code,
        label=label,
        description=description,
        is_active=is_active,
        sort_order=sort_order,
    )
    repo.add(db, item)
    await db.flush()
    ctx.record(
        db,
        action="value_list_item.created",
        target_type="value_list_item",
        target_id=str(item.id),
        target_label=_item_label(value_list, item),
        after=item.snapshot(),
    )
    return item


async def update_item(
    db: AsyncSession, ctx: AuditContext, value_list: ValueList, item: ValueListItem, changes: dict[str, Any]
) -> ValueListItem:
    if item.deleted_at is not None:
        raise AppError(409, "value_lists.item_deleted")
    before = item.snapshot()
    if "code" in changes and changes["code"] != item.code:
        _check_code(changes["code"], "value_lists.invalid_item_code")
        if await repo.get_item_by_code(db, value_list.id, changes["code"]) is not None:
            raise AppError(409, "value_lists.item_code_taken", {"code": changes["code"]})
        item.code = changes["code"]
    for field in ("label", "description", "is_active", "sort_order"):
        if field in changes:
            setattr(item, field, changes[field])
    after = item.snapshot()
    if after != before:
        ctx.record(
            db,
            action="value_list_item.updated",
            target_type="value_list_item",
            target_id=str(item.id),
            target_label=_item_label(value_list, item),
            before=before,
            after=after,
        )
    return item


async def delete_item(db: AsyncSession, ctx: AuditContext, value_list: ValueList, item: ValueListItem) -> ValueListItem:
    if item.deleted_at is not None:
        return item
    used = await item_usage(db, item)
    if used:
        raise AppError(409, "value_lists.item_in_use", {"code": item.code, "count": used})
    item.deleted_at = datetime.now(UTC)
    item.deleted_by = ctx.actor.id if ctx.actor else None
    ctx.record(
        db,
        action="value_list_item.deleted",
        target_type="value_list_item",
        target_id=str(item.id),
        target_label=_item_label(value_list, item),
        before=item.snapshot(),
    )
    return item


async def restore_item(
    db: AsyncSession, ctx: AuditContext, value_list: ValueList, item: ValueListItem
) -> ValueListItem:
    if item.deleted_at is None:
        return item
    if await repo.get_item_by_code(db, value_list.id, item.code) is not None:
        raise AppError(409, "value_lists.item_code_taken", {"code": item.code})
    item.deleted_at = None
    item.deleted_by = None
    ctx.record(
        db,
        action="value_list_item.restored",
        target_type="value_list_item",
        target_id=str(item.id),
        target_label=_item_label(value_list, item),
        after=item.snapshot(),
    )
    return item


async def reorder_items(
    db: AsyncSession, ctx: AuditContext, value_list: ValueList, item_ids: Sequence[uuid.UUID]
) -> list[ValueListItem]:
    items = list(await repo.list_items(db, value_list.id, include_deleted=False))
    by_id = {item.id: item for item in items}
    if set(item_ids) != set(by_id) or len(item_ids) != len(by_id):
        raise AppError(422, "value_lists.reorder_mismatch")
    before = [item.code for item in items]
    for position, item_id in enumerate(item_ids, start=1):
        by_id[item_id].sort_order = position * 10
    after = [by_id[item_id].code for item_id in item_ids]
    if before != after:
        ctx.record(
            db,
            action="value_list.reordered",
            target_type="value_list",
            target_id=str(value_list.id),
            target_label=value_list.code,
            before={"order": before},
            after={"order": after},
        )
    return [by_id[item_id] for item_id in item_ids]
