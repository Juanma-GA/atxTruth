"""Excel round trip for the catalogue taxonomy of one edition: Blocks, Families, Services,
Solutions and Adjacent."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.codes import CATALOGUE_CODE_RE
from app.models.catalogue import ITEM_STATUSES
from app.repositories import catalogue as repo
from app.services import catalogue as service
from app.services.excel.engine import CurrentRow, ImportContext, Key, Refs
from app.services.excel.report import Issue
from app.services.excel.spec import Column, ColumnType, DomainSpec, SheetSpec
from app.services.excel.workbook import sorted_by_code

from .common import touches, tt_fields, tt_from

_CODE = Column("code", "Code", required=True, max_length=32, width=12)
_STATUS = Column("status", "Status", ColumnType.ENUM, options=ITEM_STATUSES, default="catalogue", width=12)
_SOURCE = Column("source_ref", "Source", max_length=64, width=12)

BLOCKS = SheetSpec(
    "Blocks",
    "block",
    ("code",),
    (
        _CODE,
        Column("name", "Name", translatable=True, required=True, max_length=300, width=36),
        Column("owner", "Owner", max_length=200, special_values=True, width=22),
        Column("sort_order", "Order", ColumnType.INTEGER, min=0, max=1_000_000, width=8),
    ),
)
FAMILIES = SheetSpec(
    "Families",
    "family",
    ("code",),
    (
        _CODE,
        Column("block", "Block", ColumnType.REF, required=True, ref_sheet="Blocks", width=10),
        Column("name", "Name", translatable=True, required=True, max_length=300, width=40),
        _STATUS,
        _SOURCE,
    ),
)
SERVICES = SheetSpec(
    "Services",
    "service",
    ("code",),
    (
        _CODE,
        Column("family", "Family", ColumnType.REF, required=True, ref_sheet="Families", width=10),
        # Derived from the family: shown for reading, never imported (no double source of truth).
        Column("block", "Block (from family)", readonly=True, width=10),
        Column("name", "Name", translatable=True, required=True, max_length=300, width=44),
        _STATUS,
        _SOURCE,
    ),
)
SOLUTIONS = SheetSpec(
    "Solutions",
    "solution",
    ("code",),
    (
        _CODE,
        Column("name", "Name", translatable=True, required=True, max_length=300, width=40),
        Column("solution_types", "Solution types (1-4)", ColumnType.INT_LIST, min=1, max=4, width=14),
    ),
)
ADJACENT = SheetSpec(
    "Adjacent",
    "adjacent",
    ("code",),
    (
        _CODE,
        Column("activity", "Activity", translatable=True, required=True, max_length=300, width=44),
    ),
)
TAXONOMY_SPEC = DomainSpec(
    domain="taxonomy", format_version=1, sheets=(BLOCKS, FAMILIES, SERVICES, SOLUTIONS, ADJACENT), uses_edition=True
)
_KIND = {
    "Blocks": "block",
    "Families": "family",
    "Services": "service",
    "Solutions": "solution",
    "Adjacent": "adjacent",
}


class TaxonomyDomain:
    spec = TAXONOMY_SPEC

    async def load(self, db: AsyncSession, ctx: ImportContext) -> dict[str, dict[Key, CurrentRow]]:
        edition_id = ctx.edition.id
        blocks = {b.id: b for b in await repo.all_of(db, service.KINDS["block"].model, edition_id)}
        families = {f.id: f for f in await repo.all_of(db, service.KINDS["family"].model, edition_id)}
        current: dict[str, dict[Key, CurrentRow]] = {name: {} for name in _KIND}
        for b in blocks.values():
            current["Blocks"][(b.code,)] = CurrentRow(
                b, {"code": b.code, **tt_fields("name", b.name), "owner": b.owner, "sort_order": b.sort_order}
            )
        for f in families.values():
            current["Families"][(f.code,)] = CurrentRow(
                f,
                {
                    "code": f.code,
                    "block": blocks[f.block_id].code,
                    **tt_fields("name", f.name),
                    "status": f.status,
                    "source_ref": f.source_ref,
                },
            )
        for s in await repo.all_of(db, service.KINDS["service"].model, edition_id):
            family = families[s.family_id]
            current["Services"][(s.code,)] = CurrentRow(
                s,
                {
                    "code": s.code,
                    "family": family.code,
                    "block": blocks[family.block_id].code,
                    **tt_fields("name", s.name),
                    "status": s.status,
                    "source_ref": s.source_ref,
                },
            )
        for sol in await repo.all_of(db, service.KINDS["solution"].model, edition_id):
            current["Solutions"][(sol.code,)] = CurrentRow(
                sol, {"code": sol.code, **tt_fields("name", sol.name), "solution_types": list(sol.solution_types or [])}
            )
        for adj in await repo.all_of(db, service.KINDS["adjacent"].model, edition_id):
            current["Adjacent"][(adj.code,)] = CurrentRow(
                adj, {"code": adj.code, **tt_fields("activity", adj.activity)}
            )
        return current

    async def list_item_codes(self, db: AsyncSession) -> dict[str, set[str]]:
        return {}

    def row_issues(self, sheet: SheetSpec, key: Key, fields: dict[str, Any], current: CurrentRow | None) -> list[Issue]:
        if current is None and not CATALOGUE_CODE_RE.fullmatch(key[0]):
            return [Issue("excel.invalid_code", "Code", {"value": key[0]})]
        return []

    async def delete_blockers(self, db: AsyncSession, sheet: SheetSpec, current: CurrentRow) -> list[Issue]:
        return []  # children are checked by the engine against the final state of the file

    def _data(self, sheet: SheetSpec, fields: dict[str, Any], refs: Refs, entity: Any = None) -> dict[str, Any]:
        kind = service.KINDS[_KIND[sheet.name]]
        data: dict[str, Any] = {}
        if touches(kind.text_attr, fields):
            data[kind.text_attr] = tt_from(kind.text_attr, fields, getattr(entity, kind.text_attr) if entity else None)
        for field in kind.fields:
            if field in fields:
                data[field] = fields[field]
        if sheet is FAMILIES and "block" in fields:
            data["block_id"] = refs.id("Blocks", fields["block"])
        if sheet is SERVICES and "family" in fields:
            data["family_id"] = refs.id("Families", fields["family"])
        return data

    async def create(
        self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, fields: dict[str, Any], refs: Refs
    ) -> Any:
        kind = service.KINDS[_KIND[sheet.name]]
        data = self._data(sheet, fields, refs)
        data["code"] = fields["code"]
        return await service.create(db, ctx.audit, kind, ctx.edition, data)

    async def update(
        self,
        db: AsyncSession,
        ctx: ImportContext,
        sheet: SheetSpec,
        current: CurrentRow,
        changes: dict[str, Any],
        refs: Refs,
    ) -> None:
        kind = service.KINDS[_KIND[sheet.name]]
        await service.update(db, ctx.audit, kind, current.entity, self._data(sheet, changes, refs, current.entity))

    async def delete(self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, current: CurrentRow) -> None:
        await service.delete(db, ctx.audit, service.KINDS[_KIND[sheet.name]], current.entity)

    async def export(
        self, db: AsyncSession, ctx: ImportContext
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
        current = await self.load(db, ctx)
        rows = {name: sorted_by_code([r.fields for r in current[name].values()], "code") for name in _KIND}
        lookups = {"Blocks": [r["code"] for r in rows["Blocks"]], "Families": [r["code"] for r in rows["Families"]]}
        return rows, lookups
