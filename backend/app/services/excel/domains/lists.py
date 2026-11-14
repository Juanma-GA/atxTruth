"""Excel round trip for value lists: sheets `Lists` and `Items`."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.codes import SLUG_RE
from app.repositories import value_lists as repo
from app.services import value_lists as service
from app.services.excel.engine import CurrentRow, ImportContext, Key, Refs
from app.services.excel.report import Issue
from app.services.excel.spec import Column, ColumnType, DomainSpec, SheetSpec
from app.services.excel.workbook import sorted_by_code

from .common import touches, tt_fields, tt_from

LISTS = SheetSpec(
    name="Lists",
    entity="value_list",
    key=("code",),
    columns=(
        Column("code", "Code", required=True, max_length=64, width=22),
        Column("name", "Name", translatable=True, required=True, max_length=200, width=28),
        Column("description", "Description", translatable=True, max_length=2000, width=40),
        Column("is_system", "System", ColumnType.BOOLEAN, readonly=True, width=10),
    ),
)
ITEMS = SheetSpec(
    name="Items",
    entity="value_list_item",
    key=("list", "code"),
    columns=(
        Column("list", "List", ColumnType.REF, required=True, ref_sheet="Lists", width=20),
        Column("code", "Code", required=True, max_length=64, width=22),
        Column("label", "Label", translatable=True, required=True, max_length=200, width=28),
        Column("description", "Description", translatable=True, max_length=2000, width=36),
        Column("sort_order", "Order", ColumnType.INTEGER, min=0, max=1_000_000, width=10),
        Column("is_active", "Active", ColumnType.BOOLEAN, default=True, width=10),
    ),
)
LISTS_SPEC = DomainSpec(domain="lists", format_version=1, sheets=(LISTS, ITEMS))


class ListsDomain:
    spec = LISTS_SPEC

    async def load(self, db: AsyncSession, ctx: ImportContext) -> dict[str, dict[Key, CurrentRow]]:
        lists = {vl.id: vl for vl in await repo.list_lists(db, include_deleted=False)}
        current: dict[str, dict[Key, CurrentRow]] = {"Lists": {}, "Items": {}}
        for vl in lists.values():
            current["Lists"][(vl.code,)] = CurrentRow(
                vl,
                {
                    "code": vl.code,
                    **tt_fields("name", vl.name),
                    **tt_fields("description", vl.description),
                    "is_system": vl.is_system,
                },
            )
        for item in await repo.all_items(db):
            vl = lists[item.list_id]
            current["Items"][(vl.code, item.code)] = CurrentRow(
                item,
                {
                    "list": vl.code,
                    "code": item.code,
                    **tt_fields("label", item.label),
                    **tt_fields("description", item.description),
                    "sort_order": item.sort_order,
                    "is_active": item.is_active,
                },
            )
        return current

    async def list_item_codes(self, db: AsyncSession) -> dict[str, set[str]]:
        return {}

    def row_issues(self, sheet: SheetSpec, key: Key, fields: dict[str, Any], current: CurrentRow | None) -> list[Issue]:
        code = key[-1]
        if current is None and not SLUG_RE.fullmatch(code):
            return [Issue("excel.invalid_slug", "Code", {"value": code})]
        return []

    async def delete_blockers(self, db: AsyncSession, sheet: SheetSpec, current: CurrentRow) -> list[Issue]:
        if sheet is LISTS and current.entity.is_system:
            return [Issue("value_lists.system_list", None, {"code": current.entity.code})]
        if sheet is ITEMS:
            used = await service.item_usage(db, current.entity)
            if used:
                return [Issue("value_lists.item_in_use", None, {"code": current.entity.code, "count": used})]
        return []

    async def create(
        self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, fields: dict[str, Any], refs: Refs
    ) -> Any:
        if sheet is LISTS:
            name = tt_from("name", fields)
            assert name is not None  # noqa: S101 - required, checked by the engine
            return await service.create_list(
                db,
                ctx.audit,
                code=fields["code"],
                name=name,
                description=tt_from("description", fields),
                is_system=ctx.system_lists,
            )
        value_list = await service.get_list(db, refs.id("Lists", fields["list"]))
        label = tt_from("label", fields)
        assert label is not None  # noqa: S101
        return await service.create_item(
            db,
            ctx.audit,
            value_list,
            code=fields["code"],
            label=label,
            description=tt_from("description", fields),
            is_active=bool(fields.get("is_active", True)),
            sort_order=fields.get("sort_order"),
        )

    async def update(
        self,
        db: AsyncSession,
        ctx: ImportContext,
        sheet: SheetSpec,
        current: CurrentRow,
        changes: dict[str, Any],
        refs: Refs,
    ) -> None:
        entity = current.entity
        if sheet is LISTS:
            data: dict[str, Any] = {}
            if touches("name", changes):
                data["name"] = tt_from("name", changes, entity.name)
            if touches("description", changes):
                data["description"] = tt_from("description", changes, entity.description)
            await service.update_list(db, ctx.audit, entity, data)
            return
        value_list = await service.get_list(db, entity.list_id)
        item_data: dict[str, Any] = {k: v for k, v in changes.items() if k in ("sort_order", "is_active")}
        if item_data.get("is_active") is None:
            item_data.pop("is_active", None)
        if touches("label", changes):
            item_data["label"] = tt_from("label", changes, entity.label)
        if touches("description", changes):
            item_data["description"] = tt_from("description", changes, entity.description)
        await service.update_item(db, ctx.audit, value_list, entity, item_data)

    async def delete(self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, current: CurrentRow) -> None:
        if sheet is LISTS:
            await service.delete_list(db, ctx.audit, current.entity)
        else:
            value_list = await service.get_list(db, current.entity.list_id)
            await service.delete_item(db, ctx.audit, value_list, current.entity)

    async def export(
        self, db: AsyncSession, ctx: ImportContext
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
        current = await self.load(db, ctx)
        lists = sorted_by_code([row.fields for row in current["Lists"].values()], "code")
        list_order = {row["code"]: index for index, row in enumerate(lists)}
        items = sorted(
            (row.fields for row in current["Items"].values()),
            key=lambda r: (list_order[r["list"]], r["sort_order"], r["code"]),
        )
        return {"Lists": lists, "Items": items}, {"Lists": [row["code"] for row in lists]}
