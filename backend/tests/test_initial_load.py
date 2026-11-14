import httpx
import pytest
from openpyxl import load_workbook
from sqlalchemy import text

from app.db.base import get_sessionmaker
from app.services.excel.initial_load import build
from app.services.excel.report import Report
from app.services.excel.workbook import ExcelFileError
from tests.conftest import REFERENCE_TEMPLATE, initial_load, login, make_user, upload

EXPECTED = {"Lists": 7, "Items": 49, "Blocks": 6, "Families": 33, "Services": 86, "Solutions": 8, "Adjacent": 7}


def template_rows() -> list[tuple[object, ...]]:
    wb = load_workbook(REFERENCE_TEMPLATE, read_only=True, data_only=True)
    try:
        return [tuple(r) for r in wb["Lists"].iter_rows(values_only=True)]
    finally:
        wb.close()


async def counts() -> dict[str, int]:
    async with get_sessionmaker()() as db:
        row = (
            await db.execute(
                text(
                    "SELECT (SELECT count(*) FROM value_lists WHERE is_system),"
                    " (SELECT count(*) FROM value_list_items),"
                    " (SELECT count(*) FROM blocks), (SELECT count(*) FROM families),"
                    " (SELECT count(*) FROM families WHERE status = 'proposed'),"
                    " (SELECT count(*) FROM services), (SELECT count(*) FROM services WHERE status = 'proposed'),"
                    " (SELECT count(*) FROM solutions), (SELECT count(*) FROM adjacent_activities)"
                )
            )
        ).one()
    keys = [
        "lists",
        "items",
        "blocks",
        "families",
        "proposed_families",
        "services",
        "proposed_services",
        "solutions",
        "adjacent",
    ]
    return dict(zip(keys, row, strict=True))


async def test_analyze_writes_nothing_and_gives_exact_counts(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await upload(
        client, "/api/initial-load/analyze", REFERENCE_TEMPLATE.read_bytes(), admin_headers, REFERENCE_TEMPLATE.name
    )
    report = response.json()
    assert report["ok"] is True and report["applied"] is False
    assert {s["sheet"]: s["counts"]["create"] for s in report["sheets"]} == EXPECTED
    assert report["summary"]["special_values"] == 17
    assert report["special_values"]["unmapped"] == {"Lists!Y": 1}
    assert report["special_values"]["none"] == {"Lists!U": 1}
    assert report["special_values"]["not_applicable"] == {"Lists!K": 1, "Lists!O": 1, "Lists!U": 1}
    assert (await counts())["blocks"] == 0


async def test_apply_creates_exactly_the_v0_taxonomy_and_rerun_changes_nothing(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    report = await initial_load(client, admin_headers)
    assert report["applied"] is True
    assert await counts() == {
        "lists": 7,
        "items": 49,
        "blocks": 6,
        "families": 33,
        "proposed_families": 1,
        "services": 86,
        "proposed_services": 3,
        "solutions": 8,
        "adjacent": 7,
    }
    again = await initial_load(client, admin_headers)
    assert again["summary"]["create"] == again["summary"]["update"] == again["summary"]["delete"] == 0
    assert again["summary"]["unchanged"] == sum(EXPECTED.values())
    async with get_sessionmaker()() as db:
        excel_events = (
            await db.execute(text("SELECT count(*), min(source_detail) FROM audit_events WHERE source = 'excel'"))
        ).one()
    assert excel_events == (196, REFERENCE_TEMPLATE.name)


async def test_proposed_family_and_services(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    await initial_load(client, admin_headers)
    tree = (await client.get("/api/catalogue/V0/tree", headers=admin_headers)).json()
    b2 = next(b for b in tree["blocks"] if b["code"] == "B2")
    proposed = next(f for f in b2["families"] if f["code"] == "P-F2.6")
    assert (proposed["status"], proposed["source_ref"], proposed["name"]["en"]) == (
        "proposed",
        "CHG-01",
        "Document Management (proposed)",
    )
    assert [s["code"] for s in proposed["services"]] == ["P-S2.6.1", "P-S2.6.2", "P-S2.6.3"]
    assert all(s["status"] == "proposed" and s["source_ref"] == "CHG-01" for s in proposed["services"])
    assert all(b["owner"] is None for b in tree["blocks"])  # "To complete" → empty
    sol = {s["code"]: s["solution_types"] for s in tree["solutions"]}
    assert sol["SOL-1"] == [1]
    assert any(len(v) == 2 for v in sol.values())  # "2/4" style values become [2, 4]


async def test_rerun_keeps_translations_and_owner_entered_in_the_app(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    await initial_load(client, admin_headers)
    sector = next(
        vl for vl in (await client.get("/api/value-lists", headers=admin_headers)).json() if vl["code"] == "sector"
    )
    items = (await client.get(f"/api/value-lists/{sector['id']}", headers=admin_headers)).json()["items"]
    aero = next(i for i in items if i["code"] == "aerospace")
    await client.patch(
        f"/api/value-list-items/{aero['id']}",
        json={"label": {"en": "Aerospace", "es": "Aeroespacial", "fr": "Aérospatiale"}, "is_active": False},
        headers=admin_headers,
    )
    tree = (await client.get("/api/catalogue/V0/tree", headers=admin_headers)).json()
    b1 = tree["blocks"][0]
    await client.patch(f"/api/catalogue/block/{b1['id']}", json={"owner": "Jane Doe"}, headers=admin_headers)
    again = await initial_load(client, admin_headers)
    assert again["summary"]["update"] == 0
    item = await client.get(f"/api/value-lists/{sector['id']}", headers=admin_headers)
    aero = next(i for i in item.json()["items"] if i["code"] == "aerospace")
    assert (aero["label"]["fr"], aero["is_active"]) == ("Aérospatiale", False)
    tree = (await client.get("/api/catalogue/V0/tree", headers=admin_headers)).json()
    assert tree["blocks"][0]["owner"] == "Jane Doe"


async def test_viewer_cannot_run_the_initial_load(client: httpx.AsyncClient) -> None:
    await make_user("viewer@example.com", "viewer")
    headers = await login(client, "viewer@example.com")
    response = await upload(client, "/api/initial-load/analyze", REFERENCE_TEMPLATE.read_bytes(), headers)
    assert response.status_code == 403


def test_inconsistent_family_is_reported_not_resolved() -> None:
    rows = template_rows()
    for index, row in enumerate(rows):
        if row[14] == "S1.1.2":  # second service of F1.1: give it another family name
            changed = list(row)
            changed[17] = "Another name"
            rows[index] = tuple(changed)
    report = Report(domain="initial_load", file_name="x.xlsx")
    _lists, taxonomy = build(rows, report)
    f11 = next(r for r in taxonomy.sheets["Families"] if r.values["code"] == "F1.1")
    assert [(e.code, e.column) for e in f11.errors] == [("excel.inconsistent_family", "R")]
    assert sorted(f11.errors[0].params["values"]) == ["Another name", "Integrated Product Support (ILS) Management"]


def test_unexpected_layout_is_rejected() -> None:
    rows = template_rows()
    header = list(rows[0])
    header[14] = "Something else"
    rows[0] = tuple(header)
    with pytest.raises(ExcelFileError) as caught:
        build(rows, Report(domain="initial_load", file_name="x.xlsx"))
    assert caught.value.issue.params["column"] == "O"
