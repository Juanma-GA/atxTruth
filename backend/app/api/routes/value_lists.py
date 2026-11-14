"""Value lists: everyone signed in can read; only admins change them (checked here, server-side)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import get_current_user, require_admin
from app.db.base import get_db
from app.repositories import value_lists as repo
from app.schemas.base import sent_fields
from app.schemas.value_lists import (
    ItemCreate,
    ItemOut,
    ItemUpdate,
    ReorderRequest,
    ValueListCreate,
    ValueListDetail,
    ValueListOut,
    ValueListUpdate,
)
from app.services import value_lists as service
from app.services.audit import AuditContext

router = APIRouter(prefix="/api/value-lists", tags=["value lists"])


async def _detail(db: AsyncSession, list_id: uuid.UUID, *, include_deleted: bool) -> ValueListDetail:
    value_list = await service.get_list(db, list_id)
    items = await repo.list_items(db, list_id, include_deleted=include_deleted)
    live = [i for i in items if i.deleted_at is None]
    return ValueListDetail.model_validate(
        {
            **ValueListOut.model_validate(value_list).model_dump(),
            "item_count": len(live),
            "active_item_count": sum(1 for i in live if i.is_active),
            "items": [ItemOut.model_validate(i) for i in items],
        }
    )


@router.get("", response_model=list[ValueListOut])
async def list_lists(
    include_deleted: bool = Query(default=False),
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ValueListOut]:
    rows = await service.list_lists(db, include_deleted=include_deleted)
    return [
        ValueListOut.model_validate(
            {**ValueListOut.model_validate(vl).model_dump(), "item_count": total, "active_item_count": active}
        )
        for vl, total, active in rows
    ]


@router.post("", response_model=ValueListDetail, status_code=201)
async def create_list(
    body: ValueListCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ValueListDetail:
    value_list = await service.create_list(
        db, AuditContext(admin, request=request), code=body.code, name=body.name, description=body.description
    )
    await db.commit()
    return await _detail(db, value_list.id, include_deleted=False)


@router.get("/{list_id}", response_model=ValueListDetail)
async def get_list(
    list_id: uuid.UUID,
    include_deleted: bool = Query(default=False),
    _user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ValueListDetail:
    return await _detail(db, list_id, include_deleted=include_deleted)


@router.patch("/{list_id}", response_model=ValueListDetail)
async def update_list(
    list_id: uuid.UUID,
    body: ValueListUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ValueListDetail:
    value_list = await service.get_list(db, list_id)
    await service.update_list(db, AuditContext(admin, request=request), value_list, sent_fields(body))
    await db.commit()
    return await _detail(db, list_id, include_deleted=False)


@router.delete("/{list_id}", response_model=ValueListOut)
async def delete_list(
    list_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ValueListOut:
    value_list = await service.delete_list(
        db, AuditContext(admin, request=request), await service.get_list(db, list_id)
    )
    await db.commit()
    return ValueListOut.model_validate(value_list)


@router.post("/{list_id}/restore", response_model=ValueListDetail)
async def restore_list(
    list_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ValueListDetail:
    await service.restore_list(db, AuditContext(admin, request=request), await service.get_list(db, list_id))
    await db.commit()
    return await _detail(db, list_id, include_deleted=False)


@router.post("/{list_id}/items", response_model=ItemOut, status_code=201)
async def create_item(
    list_id: uuid.UUID,
    body: ItemCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    value_list = await service.get_list(db, list_id)
    item = await service.create_item(
        db,
        AuditContext(admin, request=request),
        value_list,
        code=body.code,
        label=body.label,
        description=body.description,
        is_active=body.is_active,
    )
    await db.commit()
    return ItemOut.model_validate(item)


@router.put("/{list_id}/order", response_model=list[ItemOut])
async def reorder_items(
    list_id: uuid.UUID,
    body: ReorderRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ItemOut]:
    value_list = await service.get_list(db, list_id)
    items = await service.reorder_items(db, AuditContext(admin, request=request), value_list, body.item_ids)
    await db.commit()
    return [ItemOut.model_validate(i) for i in items]


items_router = APIRouter(prefix="/api/value-list-items", tags=["value lists"])


@items_router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: uuid.UUID,
    body: ItemUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.get_item(db, item_id)
    value_list = await service.get_list(db, item.list_id)
    await service.update_item(db, AuditContext(admin, request=request), value_list, item, sent_fields(body))
    await db.commit()
    return ItemOut.model_validate(item)


@items_router.delete("/{item_id}", response_model=ItemOut)
async def delete_item(
    item_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.get_item(db, item_id)
    value_list = await service.get_list(db, item.list_id)
    await service.delete_item(db, AuditContext(admin, request=request), value_list, item)
    await db.commit()
    return ItemOut.model_validate(item)


@items_router.post("/{item_id}/restore", response_model=ItemOut)
async def restore_item(
    item_id: uuid.UUID,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.get_item(db, item_id)
    value_list = await service.get_list(db, item.list_id)
    await service.restore_item(db, AuditContext(admin, request=request), value_list, item)
    await db.commit()
    return ItemOut.model_validate(item)
