import io
from typing import Any

import httpx
import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import text

from app.core.codes import natural_key
from app.db.base import get_sessionmaker
from app.services.excel.domains.taxonomy import TaxonomyDomain
from tests.conftest import initial_load, login, make_user, upload


async def export(client: httpx.AsyncClient, headers: dict[str, str], domain: str) -> bytes:
    response = await client.get(f"/api/excel/{domain}/export", headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    return response.content


def cells(content: bytes) -> dict[str, list[tuple[Any, ...]]]:
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        return {name: [tuple(r) for r in wb[name].iter_rows(values_only=True)] for name in wb.sheetnames}
    finally:
        wb.close()


def edit(
    content: bytes,
    changes: dict[str, list[tuple[str, str, Any]]],
    new_rows: dict[str, list[dict[str, Any]]] | None = None,
) -> bytes:
    """changes[sheet] = [(key in first column, header, new value)]; new_rows[sheet] = [{header: value}]."""
    wb = load_workbook(io.BytesIO(content))
    for sheet, edits in changes.items():
        ws = wb[sheet]
        headers = [c.value for c in ws[1]]
        for key, header, value in edits:
            for row in ws.iter_rows(min_row=2):
                if f"{row[0].value}/{row[1].value}" == key or row[0].value == key:
                    row[headers.index(header)].value = value
                    break
            else:
                raise AssertionError(f"{key} not found in {sheet}")
    for sheet, rows in (new_rows or {}).items():
        ws = wb[sheet]
        headers = [c.value for c in ws[1]]
        for data in rows:
            ws.append([data.get(h) for h in headers])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.fixture
async def loaded(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict[str, str]:
    await initial_load(client, admin_headers)
    return admin_headers


async def test_export_is_deterministic_and_naturally_ordered(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    first, second = cells(await export(client, loaded, "taxonomy")), cells(await export(client, loaded, "taxonomy"))
    data_sheets = ["Blocks", "Families", "Services", "Solutions", "Adjacent"]
    assert [first[s] for s in data_sheets] == [second[s] for s in data_sheets]
    assert [s for s in first if not s.startswith("_")] == data_sheets
    services = [r[0] for r in first["Services"][1:]]
    assert services == sorted(services, key=natural_key)
    assert first["Services"][0] == (
        "Code",
        "Family",
        "Block (from family)",
        "Name [EN]",
        "Name [ES]",
        "Name [FR]",
        "Status",
        "Source",
        "_action",
    )
    meta = dict(r[:2] for r in first["_meta"])
    assert (meta["format"], meta["domain"], meta["edition"]) == ("atxtruth-excel", "taxonomy", "V0")


async def test_export_has_dropdowns_and_frozen_header(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    wb = load_workbook(io.BytesIO(await export(client, loaded, "taxonomy")))
    ws = wb["Services"]
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref is not None
    formulas = {dv.formula1 for dv in ws.data_validations.dataValidation}
    assert any("_lookups" in (f or "") for f in formulas)  # Family → Families codes
    assert '"catalogue,proposed"' in formulas
    assert '"delete"' in formulas
    assert wb["_lookups"].sheet_state == "hidden"


@pytest.mark.parametrize("domain", ["taxonomy", "lists"])
async def test_reimporting_an_export_changes_nothing(
    client: httpx.AsyncClient, loaded: dict[str, str], domain: str
) -> None:
    content = await export(client, loaded, domain)
    report = (await upload(client, f"/api/excel/{domain}/analyze", content, loaded)).json()
    assert report["ok"] is True
    summary = report["summary"]
    assert (summary["create"], summary["update"], summary["delete"]) == (0, 0, 0)


async def test_acceptance_four_changes_are_reported_and_applied(
    client: httpx.AsyncClient, loaded: dict[str, str]
) -> None:
    taxonomy = edit(
        await export(client, loaded, "taxonomy"),
        {"Services": [("S1.1.1", "Name [EN]", "ILS / IPS programme management"), ("S1.1.2", "Family", "F1.2")]},
    )
    lists = edit(
        await export(client, loaded, "lists"),
        {"Items": [("legacy_category/other", "_action", "delete")]},
        {
            "Items": [
                {
                    "List": "sector",
                    "Code": "medical",
                    "Label [EN]": "Medical",
                    "Label [ES]": "Médico",
                    "Label [FR]": "Médical",
                    "Order": 110,
                    "Active": "Yes",
                }
            ]
        },
    )
    tax_report = (await upload(client, "/api/excel/taxonomy/analyze", taxonomy, loaded, "taxonomy.xlsx")).json()
    list_report = (await upload(client, "/api/excel/lists/analyze", lists, loaded, "lists.xlsx")).json()
    changed = [
        (r["key"], r["action"], [c["field"] for c in r["changes"]])
        for rep in (tax_report, list_report)
        for s in rep["sheets"]
        for r in s["rows"]
        if r["action"] != "unchanged"
    ]
    assert sorted(changed) == sorted(
        [
            ("S1.1.1", "update", ["name.en"]),
            ("S1.1.2", "update", ["family"]),
            ("sector / medical", "create", ["label.en", "label.es", "label.fr", "sort_order", "is_active"]),
            ("legacy_category / other", "delete", []),
        ]
    )
    assert (await upload(client, "/api/excel/taxonomy/apply", taxonomy, loaded, "taxonomy.xlsx")).status_code == 200
    assert (await upload(client, "/api/excel/lists/apply", lists, loaded, "lists.xlsx")).status_code == 200
    tree = (await client.get("/api/catalogue/V0/tree", headers=loaded)).json()
    services = {
        s["code"]: (f["code"], s["name"]["en"]) for b in tree["blocks"] for f in b["families"] for s in f["services"]
    }
    assert services["S1.1.1"] == ("F1.1", "ILS / IPS programme management")
    assert services["S1.1.2"][0] == "F1.2"
    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT action, source, source_detail FROM audit_events WHERE source_detail IN ('taxonomy.xlsx', 'lists.xlsx')"
                )
            )
        ).all()
    assert sorted(r.action for r in rows) == [
        "service.moved",
        "service.updated",
        "value_list_item.created",
        "value_list_item.deleted",
    ]
    assert all(r.source == "excel" for r in rows)


async def test_any_error_blocks_the_whole_file(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    content = edit(
        await export(client, loaded, "taxonomy"),
        {"Services": [("S1.1.1", "Name [EN]", "Renamed"), ("S1.1.3", "Family", "F9.9")]},
    )
    analyze = (await upload(client, "/api/excel/taxonomy/analyze", content, loaded)).json()
    assert analyze["ok"] is False
    bad = next(r for s in analyze["sheets"] for r in s["rows"] if r["errors"])
    assert bad["key"] == "S1.1.3" and bad["row"] == 4
    assert bad["errors"][0] == {
        "code": "excel.unknown_reference",
        "column": "Family",
        "params": {"value": "F9.9", "sheet": "Families"},
    }
    applied = await upload(client, "/api/excel/taxonomy/apply", content, loaded)
    assert applied.status_code == 409
    assert applied.json()["error"]["code"] == "excel.has_errors"
    tree = (await client.get("/api/catalogue/V0/tree", headers=loaded)).json()
    names = {s["code"]: s["name"]["en"] for b in tree["blocks"] for f in b["families"] for s in f["services"]}
    assert names["S1.1.1"] != "Renamed"  # nothing applied


async def test_apply_is_all_or_nothing_on_unexpected_failure(
    client: httpx.AsyncClient, loaded: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    content = edit(
        await export(client, loaded, "taxonomy"),
        {"Services": [("S1.1.1", "Name [EN]", "First"), ("S1.1.2", "Name [EN]", "Second")]},
    )
    original = TaxonomyDomain.update
    calls = 0

    async def failing_update(self: TaxonomyDomain, *args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("disk full")
        await original(self, *args, **kwargs)

    monkeypatch.setattr(TaxonomyDomain, "update", failing_update)
    response = await upload(client, "/api/excel/taxonomy/apply", content, loaded)
    assert response.status_code == 500
    monkeypatch.undo()
    tree = (await client.get("/api/catalogue/V0/tree", headers=loaded)).json()
    names = {s["code"]: s["name"]["en"] for b in tree["blocks"] for f in b["families"] for s in f["services"]}
    assert names["S1.1.1"] != "First"


async def test_rows_missing_from_the_file_are_never_deleted(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    wb = load_workbook(io.BytesIO(await export(client, loaded, "taxonomy")))
    wb["Services"].delete_rows(2, 5)
    buffer = io.BytesIO()
    wb.save(buffer)
    report = (await upload(client, "/api/excel/taxonomy/apply", buffer.getvalue(), loaded)).json()
    services = next(s for s in report["sheets"] if s["sheet"] == "Services")
    assert services["counts"]["not_in_file"] == 5
    assert services["counts"]["delete"] == 0
    tree = (await client.get("/api/catalogue/V0/tree", headers=loaded)).json()
    assert sum(len(f["services"]) for b in tree["blocks"] for f in b["families"]) == 86


async def test_delete_with_children_is_an_error(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    content = edit(await export(client, loaded, "taxonomy"), {"Families": [("F6.5", "_action", "delete")]})
    report = (await upload(client, "/api/excel/taxonomy/analyze", content, loaded)).json()
    row = next(r for s in report["sheets"] for r in s["rows"] if r["key"] == "F6.5")
    assert row["errors"][0]["code"] == "excel.has_children"
    assert row["errors"][0]["params"]["children"] == ["S6.5.1", "S6.5.2"]
    # Deleting the children in the same file makes it valid.
    content = edit(content, {"Services": [("S6.5.1", "_action", "delete"), ("S6.5.2", "_action", "delete")]})
    assert (await upload(client, "/api/excel/taxonomy/analyze", content, loaded)).json()["ok"] is True


async def test_type_and_master_language_errors(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    content = edit(
        await export(client, loaded, "taxonomy"),
        {
            "Solutions": [("SOL-1", "Solution types (1-4)", "1/9")],
            "Blocks": [("B1", "Name [EN]", None)],
            "Families": [("F1.1", "Status", "maybe")],
        },
        {"Services": [{"Code": "S1.1.1", "Family": "F1.1", "Name [EN]": "Duplicate"}]},
    )
    report = (await upload(client, "/api/excel/taxonomy/analyze", content, loaded)).json()
    errors = {(r["key"], e["code"]) for s in report["sheets"] for r in s["rows"] for e in r["errors"]}
    assert ("SOL-1", "excel.too_large_value") in errors
    assert ("B1", "excel.master_language_required") in errors
    assert ("F1.1", "excel.invalid_option") in errors
    assert ("S1.1.1", "excel.duplicate_key") in errors


async def test_warnings_do_not_block(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    wb = load_workbook(io.BytesIO(await export(client, loaded, "taxonomy")))
    ws = wb["Blocks"]
    ws.cell(row=1, column=ws.max_column + 1, value="My notes")
    ws.cell(row=2, column=[c.value for c in ws[1]].index("Owner") + 1, value="To complete")  # special value
    buffer = io.BytesIO()
    wb.save(buffer)
    report = (await upload(client, "/api/excel/taxonomy/apply", buffer.getvalue(), loaded)).json()
    assert report["applied"] is True
    codes = {w["code"] for w in report["warnings"]} | {
        w["code"] for s in report["sheets"] for r in s["rows"] for w in r["warnings"]
    }
    assert {"excel.unknown_column", "excel.special_value", "excel.translation_missing"} <= codes


async def test_meta_checks(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    lists = await export(client, loaded, "lists")
    wrong = (await upload(client, "/api/excel/taxonomy/analyze", lists, loaded)).json()
    assert wrong["errors"][0]["code"] == "excel.wrong_domain"

    wb = load_workbook(io.BytesIO(await export(client, loaded, "taxonomy")))
    wb["_meta"]["B3"] = 99
    buffer = io.BytesIO()
    wb.save(buffer)
    newer = (await upload(client, "/api/excel/taxonomy/analyze", buffer.getvalue(), loaded)).json()
    assert newer["errors"][0] == {
        "code": "excel.newer_format",
        "column": None,
        "params": {"version": 99, "supported": 1},
    }

    del wb["_meta"]
    wb["_meta" if False else "Blocks"]
    buffer = io.BytesIO()
    wb.save(buffer)
    no_meta = (await upload(client, "/api/excel/taxonomy/analyze", buffer.getvalue(), loaded)).json()
    assert no_meta["ok"] is True
    assert no_meta["warnings"][0]["code"] == "excel.no_meta"


async def test_file_checks(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    not_xlsx = await upload(client, "/api/excel/lists/analyze", b"hello", admin_headers, "data.csv")
    assert not_xlsx.json()["error"]["code"] == "excel.not_xlsx"
    garbage = (await upload(client, "/api/excel/lists/analyze", b"not a zip at all", admin_headers)).json()
    assert garbage["errors"][0]["code"] == "excel.not_xlsx"
    await client.patch("/api/settings/uploads.max_excel_mb", json={"value": 0.5}, headers=admin_headers)
    big = await upload(client, "/api/excel/lists/analyze", b"x" * 600_000, admin_headers)
    assert big.status_code == 413
    empty = Workbook()
    buffer = io.BytesIO()
    empty.save(buffer)
    other = (await upload(client, "/api/excel/lists/analyze", buffer.getvalue(), admin_headers)).json()
    assert other["errors"][0]["code"] == "excel.no_known_sheet"


async def test_export_open_to_viewers_import_admin_only(client: httpx.AsyncClient, loaded: dict[str, str]) -> None:
    await make_user("viewer@example.com", "viewer")
    viewer = await login(client, "viewer@example.com")
    content = await export(client, viewer, "lists")
    assert (await upload(client, "/api/excel/lists/analyze", content, viewer)).status_code == 403
    assert (await upload(client, "/api/excel/lists/apply", content, viewer)).status_code == 403
    assert (await client.get("/api/excel/unknown/export", headers=viewer)).json()["error"][
        "code"
    ] == "excel.unknown_domain"
