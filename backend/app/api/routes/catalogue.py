"""Catalogue taxonomy: everyone signed in reads; only admins change it (checked server-side)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import get_current_user, require_admin
from app.core.errors import AppError
from app.db.base import get_db
from app.repositories import audit as audit_repo
from app.repositories import catalogue as repo
from app.schemas.base import sent_fields
from app.schemas.catalogue import (
    BlockNode,
    CatalogueCreate,
    CatalogueItemOut,
    CatalogueTree,
    CatalogueUpdate,
    EditionOut,
    FamilyNode,
    HistoryEvent,
    ServiceNode,
)
from app.services import catalogue as service
from app.services.audit import AuditContext

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])

_ALWAYS = {"code", "name", "confirm_code_change"}


def item_out(kind: service.Kind, entity: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": entity.id,
        "kind": kind.name,
        "code": entity.code,
        "name": getattr(entity, kind.text_attr),
        "deleted_at": entity.deleted_at,
        "updated_at": entity.updated_at,
    }
    for field in kind.fields:
        data[field] = getattr(entity, field)
    if kind.parent_attr:
        data[kind.parent_attr] = getattr(entity, kind.parent_attr)
    return data


def _payload(kind: service.Kind, body: dict[str, object]) -> dict[str, Any]:
    allowed = _ALWAYS | set(kind.fields) | ({kind.parent_attr} if kind.parent_attr else set())
    extra = sorted(k for k in body if k not in allowed)
    if extra:
        raise AppError(422, "catalogue.field_not_allowed", {"kind": kind.name, "fields": extra})
    data = {k: v for k, v in body.items() if k != "confirm_code_change"}
    if "name" in data:
        data[kind.text_attr] = data.pop("name")
    return data


@router.get("/editions", response_model=list[EditionOut])
async def editions(
    _user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[EditionOut]:
    return [EditionOut.model_validate(e) for e in await repo.editions(db)]


@router.get("/{edition}/tree", response_model=CatalogueTree)
async def tree(
    edition: str,
    include_deleted: bool = Query(default=False),
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CatalogueTree:
    ed = await service.edition(db, edition)
    k = service.KINDS
    blocks = service.sorted_by_code(await repo.all_of(db, k["block"].model, ed.id, include_deleted=include_deleted))
    families = service.sorted_by_code(await repo.all_of(db, k["family"].model, ed.id, include_deleted=include_deleted))
    services = service.sorted_by_code(await repo.all_of(db, k["service"].model, ed.id, include_deleted=include_deleted))
    by_family: dict[uuid.UUID, list[ServiceNode]] = {}
    for s in services:
        by_family.setdefault(s.family_id, []).append(ServiceNode.model_validate(item_out(k["service"], s)))
    by_block: dict[uuid.UUID, list[FamilyNode]] = {}
    for f in families:
        by_block.setdefault(f.block_id, []).append(
            FamilyNode.model_validate({**item_out(k["family"], f), "services": by_family.get(f.id, [])})
        )
    return CatalogueTree(
        edition=EditionOut.model_validate(ed),
        blocks=[
            BlockNode.model_validate({**item_out(k["block"], b), "families": by_block.get(b.id, [])}) for b in blocks
        ],
        solutions=[
            CatalogueItemOut.model_validate(item_out(k["solution"], s))
            for s in service.sorted_by_code(
                await repo.all_of(db, k["solution"].model, ed.id, include_deleted=include_deleted)
            )
        ],
        adjacent=[
            CatalogueItemOut.model_validate(item_out(k["adjacent"], a))
            for a in service.sorted_by_code(
                await repo.all_of(db, k["adjacent"].model, ed.id, include_deleted=include_deleted)
            )
        ],
    )


@router.post("/{edition}/{kind_name}", response_model=CatalogueItemOut, status_code=201)
async def create(
    edition: str,
    kind_name: str,
    body: CatalogueCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CatalogueItemOut:
    kind = service.kind_of(kind_name)
    ed = await service.edition(db, edition)
    entity = await service.create(
        db, AuditContext(admin, request=request), kind, ed, _payload(kind, sent_fields(body, exclude_none=True))
    )
    await db.commit()
    return CatalogueItemOut.model_validate(item_out(kind, entity))


@router.patch("/{kind_name}/{entity_id}", response_model=CatalogueItemOut)
async def update(
    kind_name: str,
    entity_id: uuid.UUID,
    body: CatalogueUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CatalogueItemOut:
    kind = service.kind_of(kind_name)
    entity = await service.get(db, kind, entity_id)
    await service.update(
        db,
        AuditContext(admin, request=request),
        kind,
        entity,
        _payload(kind, sent_fields(body)),
        confirm_code_change=body.confirm_code_change,
    )
    await db.commit()
    await db.refresh(entity)
    return CatalogueItemOut.model_validate(item_out(kind, entity))


@router.delete("/{kind_name}/{entity_id}", response_model=CatalogueItemOut)
async def delete(
    kind_name: str,
    entity_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CatalogueItemOut:
    kind = service.kind_of(kind_name)
    entity = await service.delete(
        db, AuditContext(admin, request=request), kind, await service.get(db, kind, entity_id)
    )
    await db.commit()
    await db.refresh(entity)
    return CatalogueItemOut.model_validate(item_out(kind, entity))


@router.post("/{kind_name}/{entity_id}/restore", response_model=CatalogueItemOut)
async def restore(
    kind_name: str,
    entity_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CatalogueItemOut:
    kind = service.kind_of(kind_name)
    entity = await service.restore(
        db, AuditContext(admin, request=request), kind, await service.get(db, kind, entity_id)
    )
    await db.commit()
    await db.refresh(entity)
    return CatalogueItemOut.model_validate(item_out(kind, entity))


@router.get("/{kind_name}/{entity_id}/history", response_model=list[HistoryEvent])
async def history(
    kind_name: str,
    entity_id: uuid.UUID,
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryEvent]:
    kind = service.kind_of(kind_name)
    await service.get(db, kind, entity_id)
    events = await audit_repo.for_target(db, target_type=kind.name, target_id=str(entity_id))
    return [HistoryEvent.model_validate(e) for e in events]
