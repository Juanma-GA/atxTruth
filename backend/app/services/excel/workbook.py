"""Reading and writing .xlsx files for the generic round trip.

Reading is defensive: size limit, zip check (including the uncompressed size), openpyxl in read-only
mode with defusedxml, external links not loaded, formulas read by their stored value.
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation

from app.core.codes import natural_key
from app.core.field_state import recognise
from app.services.excel.report import Issue, Report
from app.services.excel.spec import (
    ACTION_HEADER,
    DELETE_ACTION,
    FORMAT_NAME,
    LOOKUP_SHEET,
    META_SHEET,
    Column,
    ColumnType,
    DomainSpec,
    SheetSpec,
)

# An .xlsx is a zip: a tiny file can expand enormously. Uncompressed content may be at most this many
# times the upload limit (real workbooks compress about 5-10x).
MAX_EXPANSION_RATIO = 50
YES = "Yes"
NO = "No"
_TRUE = {"yes", "true", "1", "y", "si", "sí", "oui"}
_FALSE = {"no", "false", "0", "n", "non"}
_LIST_SPLIT = re.compile(r"[/,;]")


class ExcelFileError(Exception):
    """The file cannot be read as a workbook of this domain (reported as a file-level error)."""

    def __init__(self, code: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.issue = Issue(code=code, params=params or {})


# ── writing ────────────────────────────────────────────────────────────────────────────


def format_cell(column: Column, value: Any) -> Any:
    if value is None:
        return None
    if column.type == ColumnType.BOOLEAN:
        return YES if value else NO
    if column.type == ColumnType.INT_LIST:
        return "/".join(str(v) for v in value) if value else None
    return value


@dataclass
class ExportMeta:
    exported_by: str
    app_version: str
    edition: str | None = None
    exported_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def write_workbook(
    spec: DomainSpec,
    rows: dict[str, list[dict[str, Any]]],
    meta: ExportMeta,
    lookups: dict[str, list[str]],
) -> bytes:
    """`rows[sheet]` are field dicts already in their final (deterministic) order.
    `lookups[name]` are the values offered in drop-downs: a sheet name for REF columns,
    `list:<code>` for LIST_ITEM columns."""
    wb = Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    bold = Font(bold=True)

    lookup_ws = wb.create_sheet(LOOKUP_SHEET)
    lookup_ranges: dict[str, str] = {}
    for index, (name, values) in enumerate(sorted(lookups.items()), start=1):
        letter = get_column_letter(index)
        lookup_ws.cell(row=1, column=index, value=name).font = bold
        for r, value in enumerate(values, start=2):
            lookup_ws.cell(row=r, column=index, value=value)
        last = max(len(values) + 1, 2)
        lookup_ranges[name] = f"{quote_sheetname(LOOKUP_SHEET)}!${letter}$2:${letter}${last}"
    lookup_ws.sheet_state = "hidden"

    for sheet in spec.sheets:
        ws = wb.create_sheet(sheet.name)
        headers = sheet.field_headers()
        for col_index, (_field, header, _column) in enumerate(headers, start=1):
            ws.cell(row=1, column=col_index, value=header).font = bold
        action_col = len(headers) + 1
        ws.cell(row=1, column=action_col, value=ACTION_HEADER).font = bold
        data = rows.get(sheet.name, [])
        for r, record in enumerate(data, start=2):
            for col_index, (field_id, _header, column) in enumerate(headers, start=1):
                ws.cell(row=r, column=col_index, value=format_cell(column, record.get(field_id)))
        last_row = max(len(data) + 1, 2)
        # Drop-downs (data validation) where a value must come from a known set.
        validation_rows = max(last_row + 500, 1000)
        for col_index, (_field, _header, column) in enumerate(headers, start=1):
            formula = None
            if column.type == ColumnType.REF and column.ref_sheet in lookup_ranges:
                formula = f"={lookup_ranges[column.ref_sheet]}"
            elif column.type == ColumnType.LIST_ITEM and f"list:{column.list_code}" in lookup_ranges:
                formula = f"={lookup_ranges[f'list:{column.list_code}']}"
            elif column.type == ColumnType.ENUM:
                formula = '"' + ",".join(column.options) + '"'
            elif column.type == ColumnType.BOOLEAN:
                formula = f'"{YES},{NO}"'
            if formula and not column.readonly:
                letter = get_column_letter(col_index)
                dv = DataValidation(type="list", formula1=formula, allow_blank=True)
                dv.add(f"{letter}2:{letter}{validation_rows}")
                ws.add_data_validation(dv)
        letter = get_column_letter(action_col)
        dv = DataValidation(type="list", formula1=f'"{DELETE_ACTION}"', allow_blank=True)
        dv.add(f"{letter}2:{letter}{validation_rows}")
        ws.add_data_validation(dv)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(action_col)}{last_row}"
        for col_index, (_field, _header, column) in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(col_index)].width = column.width

    meta_ws = wb.create_sheet(META_SHEET)
    meta_rows: list[tuple[str, object]] = [
        ("format", FORMAT_NAME),
        ("domain", spec.domain),
        ("format_version", spec.format_version),
        ("edition", meta.edition or ""),
        ("exported_at", meta.exported_at.replace(microsecond=0).isoformat()),
        ("exported_by", meta.exported_by),
        ("app", meta.app_version),
    ]
    for r, (meta_key, meta_value) in enumerate(meta_rows, start=1):
        meta_ws.cell(row=r, column=1, value=meta_key).font = bold
        meta_ws.cell(row=r, column=2, value=meta_value)
    meta_ws.column_dimensions["A"].width = 16
    meta_ws.column_dimensions["B"].width = 40
    # Fixed document dates: the same data always gives the same workbook content.
    wb.properties.created = datetime(2026, 1, 1)
    wb.properties.modified = datetime(2026, 1, 1)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def sorted_by_code(records: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(records, key=lambda r: tuple(natural_key(str(r.get(k) or "")) for k in keys))


# ── reading ────────────────────────────────────────────────────────────────────────────


@dataclass
class ParsedRow:
    sheet: str
    row: int | None
    values: dict[str, Any]
    present: set[str]
    action: str | None = None
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)


@dataclass
class ParsedFile:
    meta: dict[str, Any] | None
    sheets: dict[str, list[ParsedRow]]
    present_fields: dict[str, set[str]]


def open_workbook(content: bytes, *, max_bytes: int) -> Any:
    if len(content) > max_bytes:
        raise ExcelFileError("excel.too_large", {"max_mb": round(max_bytes / 1_048_576, 1)})
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise ExcelFileError("excel.not_xlsx")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = set(archive.namelist())
        if "xl/workbook.xml" not in names:
            raise ExcelFileError("excel.not_xlsx")
        if sum(info.file_size for info in archive.infolist()) > max_bytes * MAX_EXPANSION_RATIO:
            raise ExcelFileError("excel.too_large", {"max_mb": round(max_bytes / 1_048_576, 1)})
    try:
        return load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:  # openpyxl raises many types for corrupt files
        raise ExcelFileError("excel.unreadable") from exc


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    elif isinstance(value, datetime):
        text = value.date().isoformat()
    else:
        text = str(value).strip()
    return text or None


def parse_cell(column: Column, raw: Any, report: Report, header: str) -> tuple[Any, list[Issue], list[Issue]]:
    """Typed value + (errors, warnings) for one cell."""
    errors: list[Issue] = []
    warnings: list[Issue] = []
    text = _text(raw)
    if column.special_values and text is not None:
        state = recognise(text)
        if state is not None:
            report.count_special(state.value, header)
            warnings.append(Issue("excel.special_value", header, {"state": state.value, "value": text}))
            return None, errors, warnings
    if text is None:
        return ([] if column.type == ColumnType.INT_LIST else None), errors, warnings
    if column.type in (ColumnType.TEXT, ColumnType.REF, ColumnType.LIST_ITEM):
        if column.max_length is not None and len(text) > column.max_length:
            errors.append(Issue("excel.too_long", header, {"max_length": column.max_length}))
        return text, errors, warnings
    if column.type == ColumnType.INTEGER:
        try:
            number = int(float(text)) if re.fullmatch(r"-?\d+(\.0+)?", text) else None
        except ValueError:
            number = None
        if number is None:
            errors.append(Issue("excel.invalid_integer", header, {"value": text}))
            return None, errors, warnings
        errors.extend(_range(column, number, header))
        return number, errors, warnings
    if column.type == ColumnType.INT_LIST:
        values: list[int] = []
        for part in _LIST_SPLIT.split(text):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit():
                errors.append(Issue("excel.invalid_integer_list", header, {"value": text}))
                return [], errors, warnings
            number = int(part)
            errors.extend(_range(column, number, header))
            values.append(number)
        return sorted(set(values)), errors, warnings
    if column.type == ColumnType.BOOLEAN:
        lowered = text.lower()
        if lowered in _TRUE:
            return True, errors, warnings
        if lowered in _FALSE:
            return False, errors, warnings
        errors.append(Issue("excel.invalid_boolean", header, {"value": text}))
        return None, errors, warnings
    if column.type == ColumnType.ENUM:
        match = next((o for o in column.options if o.lower() == text.lower()), None)
        if match is None:
            errors.append(Issue("excel.invalid_option", header, {"value": text, "options": list(column.options)}))
        return match, errors, warnings
    raise AssertionError(column.type)  # pragma: no cover


def _range(column: Column, number: int, header: str) -> list[Issue]:
    if column.min is not None and number < column.min:
        return [Issue("excel.too_small", header, {"min": column.min, "value": number})]
    if column.max is not None and number > column.max:
        return [Issue("excel.too_large_value", header, {"max": column.max, "value": number})]
    return []


def read_meta(wb: Any) -> dict[str, Any] | None:
    if META_SHEET not in wb.sheetnames:
        return None
    meta: dict[str, Any] = {}
    for row in wb[META_SHEET].iter_rows(values_only=True):
        if row and row[0] is not None:
            meta[str(row[0]).strip()] = row[1] if len(row) > 1 else None
    return meta


def check_meta(spec: DomainSpec, meta: dict[str, Any] | None, report: Report) -> None:
    if meta is None:
        report.warnings.append(Issue("excel.no_meta"))
        return
    if meta.get("format") != FORMAT_NAME or meta.get("domain") != spec.domain:
        raise ExcelFileError("excel.wrong_domain", {"expected": spec.domain, "found": str(meta.get("domain") or "")})
    try:
        version = int(meta.get("format_version") or 0)
    except (TypeError, ValueError):
        version = 0
    if version > spec.format_version:
        raise ExcelFileError("excel.newer_format", {"version": version, "supported": spec.format_version})


def parse_sheet(sheet: SheetSpec, ws: Any, report: Report) -> tuple[list[ParsedRow], set[str]]:
    rows_iter = ws.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if header_row is None:
        raise ExcelFileError("excel.empty_sheet", {"sheet": sheet.name})
    known = {header: (field_id, column) for field_id, header, column in sheet.field_headers()}
    positions: list[tuple[int, str, Column, str]] = []
    action_position: int | None = None
    present: set[str] = set()
    for index, raw in enumerate(header_row):
        header = _text(raw)
        if header is None:
            continue
        if header == ACTION_HEADER:
            action_position = index
        elif header in known:
            field_id, column = known[header]
            positions.append((index, field_id, column, header))
            present.add(field_id)
        else:
            report.warnings.append(Issue("excel.unknown_column", header, {"sheet": sheet.name}))
    for key in sheet.key:
        if key not in present:
            raise ExcelFileError("excel.missing_key_column", {"sheet": sheet.name, "column": sheet.column(key).header})

    parsed: list[ParsedRow] = []
    for row_number, raw_row in enumerate(rows_iter, start=2):
        cells = list(raw_row)
        if all(_text(c) is None for c in cells):
            continue
        row = ParsedRow(sheet=sheet.name, row=row_number, values={}, present=present)
        for index, field_id, column, header in positions:
            raw = cells[index] if index < len(cells) else None
            value, errors, warnings = parse_cell(column, raw, report, header)
            row.values[field_id] = value
            row.errors.extend(errors)
            row.warnings.extend(warnings)
        if action_position is not None and action_position < len(cells):
            action = _text(cells[action_position])
            if action is not None:
                if action.lower() == DELETE_ACTION:
                    row.action = DELETE_ACTION
                else:
                    row.errors.append(Issue("excel.invalid_action", ACTION_HEADER, {"value": action}))
        parsed.append(row)
    return parsed, present


def read_workbook(spec: DomainSpec, content: bytes, *, max_bytes: int, report: Report) -> ParsedFile:
    wb = open_workbook(content, max_bytes=max_bytes)
    try:
        meta = read_meta(wb)
        check_meta(spec, meta, report)
        sheets: dict[str, list[ParsedRow]] = {}
        present: dict[str, set[str]] = {}
        for sheet in spec.sheets:
            if sheet.name not in wb.sheetnames:
                report.warnings.append(Issue("excel.missing_sheet", None, {"sheet": sheet.name}))
                continue
            sheets[sheet.name], present[sheet.name] = parse_sheet(sheet, wb[sheet.name], report)
        if not sheets:
            raise ExcelFileError("excel.no_known_sheet", {"expected": [s.name for s in spec.sheets]})
        return ParsedFile(meta=meta, sheets=sheets, present_fields=present)
    finally:
        wb.close()
