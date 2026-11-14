"""Analyze (dry run) and Apply (one transaction) for any domain that declares a DomainSpec.

Rules shared by every entity:
- rows are matched by their stable key (code), never by position;
- a row missing from the file deletes nothing ("not in file" in the report); `_action = delete`
  soft-deletes it;
- a column missing from the file is left untouched (e.g. an initial load that only brings English);
- any error blocks the whole apply; warnings never do;
- re-importing a file just exported gives 0 changes.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.codes import natural_key
from app.core.i18n import MASTER_LANGUAGE
from app.services.audit import AuditContext
from app.services.excel.report import Change, Issue, Report, RowReport, SheetReport
from app.services.excel.spec import DELETE_ACTION, Column, ColumnType, DomainSpec, SheetSpec
from app.services.excel.workbook import ParsedFile, ParsedRow

Key = tuple[str, ...]


@dataclass
class CurrentRow:
    entity: Any
    fields: dict[str, Any]


@dataclass
class ImportContext:
    audit: AuditContext
    edition: Any = None
    # Set by the initial-load adapter: lists it creates are system lists.
    system_lists: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class Refs:
    """Resolves a code in another sheet to the entity id (existing or created in this import)."""

    def __init__(self) -> None:
        self._ids: dict[tuple[str, Key], Any] = {}

    def set(self, sheet: str, key: Key, entity_id: Any) -> None:
        self._ids[(sheet, key)] = entity_id

    def id(self, sheet: str, *key: str) -> Any:
        return self._ids[(sheet, tuple(key))]


class DomainHandler(Protocol):
    spec: DomainSpec

    async def load(self, db: AsyncSession, ctx: ImportContext) -> dict[str, dict[Key, CurrentRow]]: ...

    async def list_item_codes(self, db: AsyncSession) -> dict[str, set[str]]: ...

    def row_issues(
        self, sheet: SheetSpec, key: Key, fields: dict[str, Any], current: CurrentRow | None
    ) -> list[Issue]: ...

    async def delete_blockers(self, db: AsyncSession, sheet: SheetSpec, current: CurrentRow) -> list[Issue]: ...

    async def create(
        self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, fields: dict[str, Any], refs: Refs
    ) -> Any: ...

    async def update(
        self,
        db: AsyncSession,
        ctx: ImportContext,
        sheet: SheetSpec,
        current: CurrentRow,
        changes: dict[str, Any],
        refs: Refs,
    ) -> None: ...

    async def delete(self, db: AsyncSession, ctx: ImportContext, sheet: SheetSpec, current: CurrentRow) -> None: ...


OpKind = Literal["create", "update", "delete", "unchanged"]


@dataclass
class Op:
    kind: OpKind
    sheet: SheetSpec
    key: Key
    row: ParsedRow
    report: RowReport
    current: CurrentRow | None = None
    changes: dict[str, Any] = field(default_factory=dict)
    final: dict[str, Any] = field(default_factory=dict)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, str):
        a = a.strip() or None
    if isinstance(b, str):
        b = b.strip() or None
    if isinstance(a, list | tuple) and isinstance(b, list | tuple):
        return list(a) == list(b)
    return bool(a == b)


def _column_of(sheet: SheetSpec, field_id: str) -> Column:
    return sheet.column(field_id.split(".")[0])


def key_label(key: Key) -> str:
    return " / ".join(key)


async def analyze(
    db: AsyncSession, handler: DomainHandler, parsed: ParsedFile, ctx: ImportContext, report: Report
) -> list[Op]:
    spec = handler.spec
    current_all = await handler.load(db, ctx)
    list_items = await handler.list_item_codes(db)
    ops: list[Op] = []

    for sheet in spec.sheets:
        if sheet.name not in parsed.sheets:
            continue
        sheet_report = SheetReport(sheet=sheet.name)
        report.sheets.append(sheet_report)
        current = current_all.get(sheet.name, {})
        seen: dict[Key, int | None] = {}
        for row in parsed.sheets[sheet.name]:
            # Columns present for this row: the file's headers, or what an adapter decided to set.
            present = row.present
            key_values = tuple(row.values.get(k) for k in sheet.key)
            key: Key = tuple(str(v) for v in key_values if v is not None)
            row_report = RowReport(sheet=sheet.name, row=row.row, key=key_label(key), action="unchanged")
            row_report.errors.extend(row.errors)
            row_report.warnings.extend(row.warnings)
            sheet_report.rows.append(row_report)
            if len(key) != len(sheet.key):
                for k in sheet.key:
                    if row.values.get(k) is None:
                        row_report.errors.append(Issue("excel.required", sheet.column(k).header))
                row_report.action = "error"
                continue
            if key in seen:
                row_report.errors.append(
                    Issue(
                        "excel.duplicate_key",
                        sheet.column(sheet.key[-1]).header,
                        {"key": key_label(key), "first_row": seen[key]},
                    )
                )
                row_report.action = "error"
                continue
            seen[key] = row.row
            existing = current.get(key)
            op = Op(kind="unchanged", sheet=sheet, key=key, row=row, report=row_report, current=existing)

            if row.action == DELETE_ACTION:
                if existing is None:
                    row_report.warnings.append(Issue("excel.delete_unknown", None, {"key": key_label(key)}))
                    row_report.action = "unchanged"
                    continue
                op.kind = "delete"
                row_report.action = "delete"
                row_report.errors.extend(await handler.delete_blockers(db, sheet, existing))
                ops.append(op)
                continue

            if existing is None:
                op.kind = "create"
                row_report.action = "create"
                final: dict[str, Any] = {}
                for field_id, header, column in sheet.field_headers():
                    if column.readonly:
                        continue
                    value = row.values.get(field_id) if field_id in present else None
                    if value is None and column.default is not None:
                        value = column.default
                    final[field_id] = value
                    if field_id in present and value is not None and field_id not in sheet.key:
                        row_report.changes.append(Change(field_id, header, None, value))
                for column in sheet.columns:
                    if not column.required or column.readonly:
                        continue
                    field_id = f"{column.key}.{MASTER_LANGUAGE}" if column.translatable else column.key
                    if final.get(field_id) in (None, []):
                        code = "excel.master_language_required" if column.translatable else "excel.required"
                        row_report.errors.append(Issue(code, column.header_for(field_id)))
                op.final = final
            else:
                final = dict(existing.fields)
                for field_id, header, column in sheet.field_headers():
                    if field_id not in present or field_id in sheet.key:
                        continue
                    new_value = row.values.get(field_id)
                    old_value = existing.fields.get(field_id)
                    if new_value is None and column.default is not None:
                        continue  # an empty cell with a default (e.g. Active) keeps the current value
                    if _same(new_value, old_value):
                        continue
                    if column.readonly:
                        row_report.warnings.append(Issue("excel.readonly_ignored", header))
                        continue
                    if (
                        column.required
                        and (
                            (column.translatable and field_id.endswith(f".{MASTER_LANGUAGE}"))
                            or not column.translatable
                        )
                        and new_value in (None, [])
                    ):
                        code = "excel.master_language_required" if column.translatable else "excel.required"
                        row_report.errors.append(Issue(code, header))
                        continue
                    op.changes[field_id] = new_value
                    final[field_id] = new_value
                    row_report.changes.append(Change(field_id, header, old_value, new_value))
                op.final = final
                if op.changes:
                    op.kind = "update"
                    row_report.action = "update"

            # Translations that stay empty (only for languages whose column is in the file).
            for column in sheet.columns:
                if not column.translatable or column.readonly:
                    continue
                if not op.final.get(f"{column.key}.{MASTER_LANGUAGE}"):
                    continue  # nothing to translate (an empty optional text)
                missing = [
                    f.rsplit(".", 1)[1]
                    for f in column.fields()
                    if f in present and not f.endswith(f".{MASTER_LANGUAGE}") and not op.final.get(f)
                ]
                if missing:
                    row_report.warnings.append(
                        Issue("excel.translation_missing", column.header, {"languages": missing})
                    )
            # A translation without the master text is not valid (TranslatableText needs English).
            for column in sheet.columns:
                if column.translatable and not column.readonly and not op.final.get(f"{column.key}.{MASTER_LANGUAGE}"):
                    if any(op.final.get(f) for f in column.fields()) and not any(
                        i.code == "excel.master_language_required" for i in row_report.errors
                    ):
                        row_report.errors.append(
                            Issue(
                                "excel.master_language_required", column.header_for(f"{column.key}.{MASTER_LANGUAGE}")
                            )
                        )
            row_report.errors.extend(handler.row_issues(sheet, key, op.final, existing))
            ops.append(op)

        mentioned = {op.key for op in ops if op.sheet is sheet} | set(seen)
        sheet_report.not_in_file = sorted((key_label(k) for k in current if k not in mentioned), key=natural_key)

    _check_references(spec, ops, current_all, list_items)
    _check_children(spec, ops, current_all, parsed)
    return ops


def _final_keys(spec: DomainSpec, ops: list[Op], current_all: dict[str, dict[Key, CurrentRow]]) -> dict[str, set[Key]]:
    keys: dict[str, set[Key]] = {s.name: set(current_all.get(s.name, {})) for s in spec.sheets}
    for op in ops:
        if op.kind == "delete":
            keys[op.sheet.name].discard(op.key)
        elif op.kind == "create" and not op.report.errors:
            keys[op.sheet.name].add(op.key)
    return keys


def _check_references(
    spec: DomainSpec, ops: list[Op], current_all: dict[str, dict[Key, CurrentRow]], list_items: dict[str, set[str]]
) -> None:
    final_keys = _final_keys(spec, ops, current_all)
    for op in ops:
        if op.kind == "delete":
            continue
        for column in op.sheet.columns:
            if column.readonly or column.type not in (ColumnType.REF, ColumnType.LIST_ITEM):
                continue
            value = op.final.get(column.key)
            if value is None:
                continue
            if column.type == ColumnType.REF and column.ref_sheet is not None:
                if (str(value),) not in final_keys.get(column.ref_sheet, set()):
                    op.report.errors.append(
                        Issue("excel.unknown_reference", column.header, {"value": value, "sheet": column.ref_sheet})
                    )
            elif column.type == ColumnType.LIST_ITEM and column.list_code is not None:
                if str(value) not in list_items.get(column.list_code, set()):
                    op.report.errors.append(
                        Issue("excel.unknown_list_item", column.header, {"value": value, "list": column.list_code})
                    )


def _check_children(
    spec: DomainSpec, ops: list[Op], current_all: dict[str, dict[Key, CurrentRow]], parsed: ParsedFile
) -> None:
    """A row cannot be deleted while rows of another sheet still point at it."""
    deletes = {(op.sheet.name, op.key): op for op in ops if op.kind == "delete"}
    if not deletes:
        return
    by_key = {(op.sheet.name, op.key): op for op in ops}
    for child in spec.sheets:
        for column in child.refs():
            if column.readonly or column.ref_sheet is None:
                continue
            children: dict[Key, list[str]] = {}
            rows: dict[Key, Any] = {}
            for key, cur in current_all.get(child.name, {}).items():
                op = by_key.get((child.name, key))
                if op is not None and op.kind == "delete":
                    continue
                rows[key] = (op.final if op is not None else cur.fields).get(column.key)
            for op in ops:
                if op.sheet is child and op.kind == "create":
                    rows[op.key] = op.final.get(column.key)
            for key, parent in rows.items():
                if parent is not None:
                    children.setdefault((str(parent),), []).append(key_label(key))
            for (sheet_name, parent_key), op in deletes.items():
                if sheet_name == column.ref_sheet and parent_key in children:
                    op.report.errors.append(
                        Issue(
                            "excel.has_children",
                            None,
                            {"sheet": child.name, "children": sorted(children[parent_key], key=natural_key)},
                        )
                    )


async def apply(db: AsyncSession, handler: DomainHandler, ops: list[Op], ctx: ImportContext) -> None:
    """Writes the plan. The caller commits (or rolls back) the transaction."""
    spec = handler.spec
    current_all = await handler.load(db, ctx)
    refs = Refs()
    for sheet_name, rows in current_all.items():
        for key, cur in rows.items():
            refs.set(sheet_name, key, cur.entity.id)
    for sheet in spec.sheets:
        for op in ops:
            if op.sheet is not sheet:
                continue
            if op.kind == "create":
                entity = await handler.create(db, ctx, sheet, op.final, refs)
                refs.set(sheet.name, op.key, entity.id)
            elif op.kind == "update":
                current = current_all[sheet.name][op.key]
                await handler.update(db, ctx, sheet, current, op.changes, refs)
    for sheet in reversed(spec.sheets):
        for op in ops:
            if op.sheet is sheet and op.kind == "delete":
                await handler.delete(db, ctx, sheet, current_all[sheet.name][op.key])
