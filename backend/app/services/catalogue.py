"""Catalogue taxonomy: blocks → families → services, solutions and adjacent activities.

The block of a service is derived from its family. Codes are unique per edition and kind. A block or
family with active children cannot be deleted. Changing a code needs explicit confirmation (an Excel
exported before will no longer match that row). Operations never commit: the caller does.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.codes import CATALOGUE_CODE_RE, natural_key
from app.core.errors import AppError
from app.models import AdjacentActivity, Block, CatalogueEdition, Family, Service, Solution
from app.models.catalogue import ITEM_STATUSES
from app.repositories import catalogue as repo
from app.schemas.translatable import TranslatableText
from app.services.audit import AuditContext

SOLUTION_TYPE_RANGE = (1, 4)


@dataclass(frozen=True)
class Kind:
    name: str
    model: Any
    text_attr: str  # "name", or "activity" for adjacent activities
    fields: tuple[str, ...]  # editable fields besides code and text
    parent_attr: str | None = None
    parent_kind: str | None = None
    child_kind: str | None = None


KINDS: dict[str, Kind] = {
    "block": Kind("block", Block, "name", ("owner", "sort_order"), child_kind="family"),
    "family": Kind("family", Family, "name", ("status", "source_ref"), "block_id", "block", "service"),
    "service": Kind("service", Service, "name", ("status", "source_ref"), "family_id", "family"),
    "solution": Kind("solution", Solution, "name", ("solution_types",)),
    "adjacent": Kind("adjacent", AdjacentActivity, "activity", ()),
}


def kind_of(name: str) -> Kind:
    if name not in KINDS:
        raise AppError(404, "catalogue.unknown_kind", {"kind": name})
    return KINDS[name]


def snapshot(kind: Kind, entity: Any) -> dict[str, Any]:
    text: TranslatableText = getattr(entity, kind.text_attr)
    data: dict[str, Any] = {"code": entity.code, kind.text_attr: text.to_db()}
    for field in kind.fields:
        data[field] = getattr(entity, field)
    if kind.parent_attr:
        data[kind.parent_attr] = str(getattr(entity, kind.parent_attr))
    return data


async def edition(db: AsyncSession, code: str) -> CatalogueEdition:
    found = await repo.edition_by_code(db, code)
    if found is None:
        raise AppError(404, "catalogue.edition_not_found", {"edition": code})
    return found


async def get(db: AsyncSession, kind: Kind, entity_id: uuid.UUID) -> Any:
    entity = await repo.get(db, kind.model, entity_id)
    if entity is None:
        raise AppError(404, "catalogue.not_found", {"kind": kind.name})
    return entity


def sorted_by_code(entities: Any) -> list[Any]:
    return sorted(entities, key=lambda e: natural_key(e.code))


async def _check_code(db: AsyncSession, kind: Kind, edition_id: uuid.UUID, code: str) -> None:
    if not CATALOGUE_CODE_RE.fullmatch(code):
        raise AppError(422, "catalogue.invalid_code", {"code": code})
    if await repo.by_code(db, kind.model, edition_id, code) is not None:
        raise AppError(409, "catalogue.code_taken", {"code": code, "kind": kind.name})


async def _check_parent(db: AsyncSession, kind: Kind, edition_id: uuid.UUID, parent_id: uuid.UUID) -> Any:
    assert kind.parent_kind is not None  # noqa: S101
    parent = await repo.get(db, KINDS[kind.parent_kind].model, parent_id)
    if parent is None or parent.deleted_at is not None or parent.edition_id != edition_id:
        raise AppError(422, "catalogue.parent_not_found", {"kind": kind.parent_kind})
    return parent


def _check_fields(changes: dict[str, Any]) -> None:
    if "status" in changes and changes["status"] not in ITEM_STATUSES:
        raise AppError(422, "catalogue.invalid_status", {"status": changes["status"]})
    if "solution_types" in changes:
        low, high = SOLUTION_TYPE_RANGE
        values = changes["solution_types"] or []
        if any(not isinstance(v, int) or not low <= v <= high for v in values):
            raise AppError(422, "catalogue.invalid_solution_type", {"min": low, "max": high})
        changes["solution_types"] = sorted(set(values))


async def create(db: AsyncSession, ctx: AuditContext, kind: Kind, ed: CatalogueEdition, data: dict[str, Any]) -> Any:
    await _check_code(db, kind, ed.id, data["code"])
    _check_fields(data)
    values: dict[str, Any] = {"edition_id": ed.id, "code": data["code"], kind.text_attr: data[kind.text_attr]}
    if kind.parent_attr:
        if data.get(kind.parent_attr) is None:
            raise AppError(422, "catalogue.parent_required", {"kind": kind.parent_kind})
        await _check_parent(db, kind, ed.id, data[kind.parent_attr])
        values[kind.parent_attr] = data[kind.parent_attr]
    for field in kind.fields:
        if field in data and data[field] is not None:
            values[field] = data[field]
    entity = kind.model(**values)
    repo.add(db, entity)
    await db.flush()
    ctx.record(
        db,
        action=f"{kind.name}.created",
        target_type=kind.name,
        target_id=str(entity.id),
        target_label=entity.code,
        after=snapshot(kind, entity),
    )
    return entity


async def update(
    db: AsyncSession,
    ctx: AuditContext,
    kind: Kind,
    entity: Any,
    changes: dict[str, Any],
    *,
    confirm_code_change: bool = False,
) -> Any:
    if entity.deleted_at is not None:
        raise AppError(409, "catalogue.deleted", {"kind": kind.name})
    before = snapshot(kind, entity)
    action = f"{kind.name}.updated"
    if "code" in changes and changes["code"] != entity.code:
        if not confirm_code_change:
            raise AppError(409, "catalogue.code_change_needs_confirmation", {"code": entity.code})
        await _check_code(db, kind, entity.edition_id, changes["code"])
        entity.code = changes["code"]
        action = f"{kind.name}.code_changed"
    _check_fields(changes)
    if (
        kind.parent_attr
        and kind.parent_attr in changes
        and changes[kind.parent_attr] != getattr(entity, kind.parent_attr)
    ):
        await _check_parent(db, kind, entity.edition_id, changes[kind.parent_attr])
        setattr(entity, kind.parent_attr, changes[kind.parent_attr])
        if action == f"{kind.name}.updated":
            action = f"{kind.name}.moved"
    if kind.text_attr in changes and changes[kind.text_attr] is not None:
        setattr(entity, kind.text_attr, changes[kind.text_attr])
    for field in kind.fields:
        if field in changes:
            setattr(entity, field, changes[field])
    after = snapshot(kind, entity)
    if after != before:
        ctx.record(
            db,
            action=action,
            target_type=kind.name,
            target_id=str(entity.id),
            target_label=entity.code,
            before=before,
            after=after,
        )
    return entity


async def children_of(db: AsyncSession, kind: Kind, entity: Any) -> list[str]:
    if kind.child_kind is None:
        return []
    child = KINDS[kind.child_kind]
    assert child.parent_attr is not None  # noqa: S101
    return sorted(await repo.active_children(db, child.model, child.parent_attr, entity.id), key=natural_key)


async def delete(db: AsyncSession, ctx: AuditContext, kind: Kind, entity: Any) -> Any:
    if entity.deleted_at is not None:
        return entity
    children = await children_of(db, kind, entity)
    if children:
        raise AppError(409, "catalogue.has_children", {"code": entity.code, "children": children})
    entity.deleted_at = datetime.now(UTC)
    entity.deleted_by = ctx.actor.id if ctx.actor else None
    ctx.record(
        db,
        action=f"{kind.name}.deleted",
        target_type=kind.name,
        target_id=str(entity.id),
        target_label=entity.code,
        before=snapshot(kind, entity),
    )
    return entity


async def restore(db: AsyncSession, ctx: AuditContext, kind: Kind, entity: Any) -> Any:
    if entity.deleted_at is None:
        return entity
    if await repo.by_code(db, kind.model, entity.edition_id, entity.code) is not None:
        raise AppError(409, "catalogue.code_taken", {"code": entity.code, "kind": kind.name})
    if kind.parent_attr:
        await _check_parent(db, kind, entity.edition_id, getattr(entity, kind.parent_attr))
    entity.deleted_at = None
    entity.deleted_by = None
    ctx.record(
        db,
        action=f"{kind.name}.restored",
        target_type=kind.name,
        target_id=str(entity.id),
        target_label=entity.code,
        after=snapshot(kind, entity),
    )
    return entity
