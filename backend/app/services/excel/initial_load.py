"""Initial load adapter: "From CS_Reference_Template (sheet Lists)".

Converts the Lists sheet of sources/excel/CS_Reference_Template_v0.6.xlsx into the app's own
format (value lists + taxonomy of edition V0) and runs it through the SAME Analyze/Apply engine and
report. Special values ("To complete", "N/A", "None", "To check" in the adjacent column) are not
created: they are counted in the report. Running it again changes nothing.

Only the columns the template really carries are set (English labels, codes, parents, status):
ES/FR translations, item order, the active flag and block owners entered later in the app are never
overwritten by a re-run.
"""

import re
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from openpyxl.utils import column_index_from_string
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.core.codes import slugify
from app.core.errors import AppError
from app.core.field_state import FieldState, recognise
from app.repositories import catalogue as catalogue_repo
from app.services.audit import AuditContext
from app.services.excel import engine
from app.services.excel.domains.lists import ListsDomain
from app.services.excel.domains.taxonomy import TaxonomyDomain
from app.services.excel.report import Issue, Report
from app.services.excel.service import DEFAULT_EDITION, finish, max_bytes
from app.services.excel.workbook import ExcelFileError, ParsedFile, ParsedRow, open_workbook

SHEET = "Lists"
SOURCE = f"{SHEET}!"


@dataclass(frozen=True)
class ListSource:
    code: str
    column: str
    header: str
    name: str


LIST_SOURCES = (
    ListSource("sector", "A", "Sector", "Sector"),
    ListSource("iqp", "C", "IQP", "IQP"),
    ListSource("review_status", "E", "Review status", "Review status"),
    ListSource("yes_no_check", "G", "Yes / No / To check", "Yes / No / To check"),
    ListSource("scope", "I", "Scope", "Scope"),
    ListSource("delivery_model", "AB", "Delivery model (values)", "Delivery model"),
    ListSource("legacy_category", "AD", "Legacy category", "Legacy category"),
)
# Header expected in row 1 of each taxonomy column (the layout of CS_Reference_Template v0.6).
TAXONOMY_HEADERS = {
    "K": "Block ID",
    "L": "Block name",
    "M": "Owner",
    "O": "Service ID",
    "P": "Service",
    "Q": "Family ID",
    "R": "Family",
    "S": "Block",
    "T": "Source",
    "U": "Solution ID",
    "V": "Solution",
    "W": "A&D CCX solution type",
    "Y": "Adjacent ID",
    "Z": "Activity",
}
BLOCK_CODE = re.compile(r"^B\d+$")
SERVICE_CODE = re.compile(r"^(P-)?S\d+(\.\d+)+$")
SOLUTION_CODE = re.compile(r"^SOL-\d+$")
ADJACENT_CODE = re.compile(r"^ADJ-\d+$")
CHANGE_REF = re.compile(r"CHG-\d+")
# "To check" in the Adjacent ID column means "no adjacent entry fits".
ADJACENT_UNMAPPED = "to check"


def _cell(row: tuple[Any, ...], column: str) -> str | None:
    index = column_index_from_string(column) - 1
    value = row[index] if index < len(row) else None
    if value is None:
        return None
    text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
    return text or None


def _status(source: str | None) -> tuple[str, str | None]:
    if source and source.lower().startswith("proposed"):
        match = CHANGE_REF.search(source)
        return "proposed", match.group(0) if match else None
    return "catalogue", None


class _Builder:
    def __init__(self, report: Report) -> None:
        self.report = report
        self.lists: list[ParsedRow] = []
        self.items: list[ParsedRow] = []
        self.blocks: list[ParsedRow] = []
        self.families: dict[str, ParsedRow] = {}
        self.services: list[ParsedRow] = []
        self.solutions: list[ParsedRow] = []
        self.adjacent: list[ParsedRow] = []

    def special(self, state: FieldState, column: str) -> None:
        self.report.count_special(state.value, f"{SOURCE}{column}")

    def row(self, sheet: str, number: int, values: dict[str, Any]) -> ParsedRow:
        return ParsedRow(sheet=sheet, row=number, values=values, present=set(values))


def _check_layout(header: tuple[Any, ...]) -> None:
    expected = {s.column: s.header for s in LIST_SOURCES} | TAXONOMY_HEADERS
    for column, text in expected.items():
        found = _cell(header, column) or ""
        if not found.startswith(text):
            raise ExcelFileError("excel.unexpected_layout", {"column": column, "expected": text, "found": found})


def build(rows: list[tuple[Any, ...]], report: Report) -> tuple[ParsedFile, ParsedFile]:
    _check_layout(rows[0])
    b = _Builder(report)
    data = list(enumerate(rows[1:], start=2))

    for source in LIST_SOURCES:
        b.lists.append(b.row("Lists", 1, {"code": source.code, "name.en": source.name}))
        for number, row in data:
            text = _cell(row, source.column)
            if text is None:
                continue
            state = recognise(text)
            if state is not None:
                b.special(state, source.column)
                continue
            b.items.append(b.row("Items", number, {"list": source.code, "code": slugify(text), "label.en": text}))

    for number, row in data:
        code = _cell(row, "K")
        if code is None:
            continue
        if not BLOCK_CODE.fullmatch(code):
            state = recognise(code)
            if state is not None:
                b.special(state, "K")
            continue
        values: dict[str, Any] = {"code": code, "name.en": _cell(row, "L")}
        owner = _cell(row, "M")
        owner_state = recognise(owner)
        if owner_state is not None:
            b.special(owner_state, "M")  # owner stays as it is in the app (empty = to complete)
        else:
            values["owner"] = owner
        b.blocks.append(b.row("Blocks", number, values))

    family_sources: dict[str, list[tuple[int, str | None, str | None]]] = {}
    for number, row in data:
        code = _cell(row, "O")
        if code is None:
            continue
        if not SERVICE_CODE.fullmatch(code):
            state = recognise(code)
            if state is not None:
                b.special(state, "O")
            continue
        status, source_ref = _status(_cell(row, "T"))
        family_code = _cell(row, "Q")
        b.services.append(
            b.row(
                "Services",
                number,
                {
                    "code": code,
                    "family": family_code,
                    "name.en": _cell(row, "P"),
                    "status": status,
                    "source_ref": source_ref,
                },
            )
        )
        if family_code is None:
            continue
        family_sources.setdefault(family_code, []).append((number, _cell(row, "R"), _cell(row, "S")))
        if family_code not in b.families:
            b.families[family_code] = b.row(
                "Families",
                number,
                {
                    "code": family_code,
                    "block": _cell(row, "S"),
                    "name.en": _cell(row, "R"),
                    "status": status,
                    "source_ref": source_ref,
                },
            )

    # A family described differently in two rows is reported, never resolved by picking one (HR7).
    for family_code, seen in family_sources.items():
        names = sorted({name or "" for _n, name, _b in seen})
        blocks = sorted({block or "" for _n, _name, block in seen})
        parsed_row = b.families[family_code]
        if len(names) > 1:
            parsed_row.errors.append(Issue("excel.inconsistent_family", "R", {"code": family_code, "values": names}))
        if len(blocks) > 1:
            parsed_row.errors.append(Issue("excel.inconsistent_family", "S", {"code": family_code, "values": blocks}))

    for number, row in data:
        code = _cell(row, "U")
        if code is None:
            continue
        if not SOLUTION_CODE.fullmatch(code):
            state = recognise(code)
            if state is not None:
                b.special(state, "U")
            continue
        raw_types = _cell(row, "W") or ""
        types = sorted({int(p) for p in re.split(r"[/,;]", raw_types) if p.strip().isdigit()})
        b.solutions.append(
            b.row("Solutions", number, {"code": code, "name.en": _cell(row, "V"), "solution_types": types})
        )

    for number, row in data:
        code = _cell(row, "Y")
        if code is None:
            continue
        if not ADJACENT_CODE.fullmatch(code):
            if code.lower() == ADJACENT_UNMAPPED:
                b.special(FieldState.UNMAPPED, "Y")
            elif (state := recognise(code)) is not None:
                b.special(state, "Y")
            continue
        b.adjacent.append(b.row("Adjacent", number, {"code": code, "activity.en": _cell(row, "Z")}))

    lists_file = ParsedFile(meta=None, sheets={"Lists": b.lists, "Items": b.items}, present_fields={})
    taxonomy_file = ParsedFile(
        meta=None,
        sheets={
            "Blocks": b.blocks,
            "Families": list(b.families.values()),
            "Services": b.services,
            "Solutions": b.solutions,
            "Adjacent": b.adjacent,
        },
        present_fields={},
    )
    return lists_file, taxonomy_file


async def run(
    db: AsyncSession, content: bytes, file_name: str, actor: CurrentUser | None, request: Request | None, *, apply: bool
) -> Report:
    report = Report(domain="initial_load", file_name=file_name)
    try:
        wb = open_workbook(content, max_bytes=await max_bytes(db))
        try:
            if SHEET not in wb.sheetnames:
                raise ExcelFileError("excel.missing_sheet", {"sheet": SHEET})
            rows = list(wb[SHEET].iter_rows(values_only=True))
        finally:
            wb.close()
        if not rows:
            raise ExcelFileError("excel.empty_sheet", {"sheet": SHEET})
        lists_file, taxonomy_file = build(rows, report)
    except ExcelFileError as exc:
        report.errors.append(exc.issue)
        if apply:
            raise AppError(409, "excel.has_errors", {"report": report.as_dict()}) from None
        return report

    edition = await catalogue_repo.edition_by_code(db, DEFAULT_EDITION)
    if edition is None:
        raise AppError(404, "catalogue.edition_not_found", {"edition": DEFAULT_EDITION})
    audit = AuditContext(actor, request=request, source="excel", source_detail=file_name[:255])
    lists_ctx = engine.ImportContext(audit=audit, system_lists=True)
    taxonomy_ctx = engine.ImportContext(audit=audit, edition=edition)
    lists, taxonomy = ListsDomain(), TaxonomyDomain()
    lists_ops = await engine.analyze(db, lists, lists_file, lists_ctx, report)
    taxonomy_ops = await engine.analyze(db, taxonomy, taxonomy_file, taxonomy_ctx, report)
    return await finish(db, report, [(lists, lists_ctx, lists_ops), (taxonomy, taxonomy_ctx, taxonomy_ops)], apply)
