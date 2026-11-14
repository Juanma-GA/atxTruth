from typing import Any

import httpx
import pytest

from tests.conftest import audit_actions, initial_load, login, make_user


@pytest.fixture
async def tree(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict[str, Any]:
    await initial_load(client, admin_headers)
    return dict((await client.get("/api/catalogue/V0/tree", headers=admin_headers)).json())


def find(tree: dict[str, Any], code: str) -> dict[str, Any]:
    for block in tree["blocks"]:
        if block["code"] == code:
            return dict(block)
        for family in block["families"]:
            if family["code"] == code:
                return dict(family)
            for service in family["services"]:
                if service["code"] == code:
                    return dict(service)
    raise KeyError(code)


async def test_tree_is_naturally_ordered(tree: dict[str, Any]) -> None:
    assert [b["code"] for b in tree["blocks"]] == ["B1", "B2", "B3", "B4", "B5", "B6"]
    b2 = [f["code"] for f in tree["blocks"][1]["families"]]
    assert b2[-1] == "P-F2.6" and b2.index("P-F2.6") == b2.index("F2.5") + 1
    assert [s["code"] for s in tree["solutions"]] == [f"SOL-{i}" for i in range(1, 9)]
    assert [a["code"] for a in tree["adjacent"]] == [f"ADJ-{i}" for i in range(1, 8)]


async def test_block_with_families_cannot_be_deleted(
    client: httpx.AsyncClient, admin_headers: dict[str, str], tree: dict[str, Any]
) -> None:
    b2 = find(tree, "B2")
    response = await client.delete(f"/api/catalogue/block/{b2['id']}", headers=admin_headers)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "catalogue.has_children"
    assert error["params"]["children"] == [f["code"] for f in b2["families"]]


async def test_code_change_needs_confirmation_and_is_audited(
    client: httpx.AsyncClient, admin_headers: dict[str, str], tree: dict[str, Any]
) -> None:
    service = find(tree, "S1.1.1")
    refused = await client.patch(
        f"/api/catalogue/service/{service['id']}", json={"code": "S1.1.9"}, headers=admin_headers
    )
    assert refused.json()["error"]["code"] == "catalogue.code_change_needs_confirmation"
    taken = await client.patch(
        f"/api/catalogue/service/{service['id']}",
        json={"code": "S1.1.2", "confirm_code_change": True},
        headers=admin_headers,
    )
    assert taken.json()["error"]["code"] == "catalogue.code_taken"
    changed = await client.patch(
        f"/api/catalogue/service/{service['id']}",
        json={"code": "S1.1.9", "confirm_code_change": True},
        headers=admin_headers,
    )
    assert (changed.json()["code"], changed.json()["id"]) == ("S1.1.9", service["id"])  # same UUID
    history = (await client.get(f"/api/catalogue/service/{service['id']}/history", headers=admin_headers)).json()
    assert history[0]["action"] == "service.code_changed"
    assert (history[0]["before"]["code"], history[0]["after"]["code"]) == ("S1.1.1", "S1.1.9")
    assert history[-1]["source"] == "excel"  # created by the initial load


async def test_move_service_and_edit_names(
    client: httpx.AsyncClient, admin_headers: dict[str, str], tree: dict[str, Any]
) -> None:
    service, target = find(tree, "S1.1.1"), find(tree, "F2.1")
    moved = await client.patch(
        f"/api/catalogue/service/{service['id']}", json={"family_id": target["id"]}, headers=admin_headers
    )
    assert moved.json()["family_id"] == target["id"]
    renamed = await client.patch(
        f"/api/catalogue/service/{service['id']}",
        json={
            "name": {
                "en": "ILS programme management",
                "es": "Gestión del programa ILS",
                "fr": "Gestion du programme ILS",
            }
        },
        headers=admin_headers,
    )
    assert renamed.json()["name"]["es"] == "Gestión del programa ILS"
    assert {"service.moved", "service.updated"} <= set(await audit_actions("S1.1.1"))


async def test_create_delete_restore(
    client: httpx.AsyncClient, admin_headers: dict[str, str], tree: dict[str, Any]
) -> None:
    b1 = find(tree, "B1")
    family = await client.post(
        "/api/catalogue/V0/family",
        json={
            "code": "F1.9",
            "name": {"en": "New family"},
            "block_id": b1["id"],
            "status": "proposed",
            "source_ref": "CHG-02",
        },
        headers=admin_headers,
    )
    assert family.status_code == 201, family.text
    fid = family.json()["id"]
    deleted = await client.delete(f"/api/catalogue/family/{fid}", headers=admin_headers)
    assert deleted.json()["deleted_at"] is not None
    restored = await client.post(f"/api/catalogue/family/{fid}/restore", headers=admin_headers)
    assert restored.json()["deleted_at"] is None
    wrong_field = await client.post(
        "/api/catalogue/V0/adjacent", json={"code": "ADJ-9", "name": {"en": "X"}, "owner": "Me"}, headers=admin_headers
    )
    assert wrong_field.json()["error"]["code"] == "catalogue.field_not_allowed"
    bad_types = await client.post(
        "/api/catalogue/V0/solution",
        json={"code": "SOL-9", "name": {"en": "X"}, "solution_types": [5]},
        headers=admin_headers,
    )
    assert bad_types.json()["error"]["code"] == "catalogue.invalid_solution_type"


@pytest.mark.parametrize("role", ["editor", "viewer"])
async def test_only_admin_edits_catalogue(client: httpx.AsyncClient, tree: dict[str, Any], role: str) -> None:
    await make_user(f"{role}@example.com", role)
    headers = await login(client, f"{role}@example.com")
    assert (await client.get("/api/catalogue/V0/tree", headers=headers)).status_code == 200
    service = find(tree, "S1.1.1")
    assert (await client.get(f"/api/catalogue/service/{service['id']}/history", headers=headers)).status_code == 200
    for method, url, body in [
        ("PATCH", f"/api/catalogue/service/{service['id']}", {"name": {"en": "X"}}),
        ("DELETE", f"/api/catalogue/service/{service['id']}", None),
        ("POST", "/api/catalogue/V0/block", {"code": "B9", "name": {"en": "X"}}),
    ]:
        assert (await client.request(method, url, json=body, headers=headers)).status_code == 403


async def test_unknown_edition_and_kind(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    assert (await client.get("/api/catalogue/V9/tree", headers=admin_headers)).json()["error"][
        "code"
    ] == "catalogue.edition_not_found"
    editions = (await client.get("/api/catalogue/editions", headers=admin_headers)).json()
    assert [e["code"] for e in editions] == ["V0"]
