import httpx
import pytest

from app.services import value_lists as service
from tests.conftest import audit_actions, login, make_user


def tt(en: str, es: str | None = None, fr: str | None = None) -> dict[str, str]:
    return {k: v for k, v in {"en": en, "es": es, "fr": fr}.items() if v}


async def create_list(client: httpx.AsyncClient, headers: dict[str, str], code: str = "contract_type") -> dict:  # type: ignore[type-arg]
    response = await client.post(
        "/api/value-lists",
        json={"code": code, "name": tt("Contract type", "Tipo de contrato", "Type de contrat")},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_admin_creates_list_with_items_reorders_and_deactivates(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    value_list = await create_list(client, admin_headers)
    ids = []
    for en, es, fr in [
        ("Fixed price", "Precio cerrado", "Forfait"),
        ("Time & material", "Por horas", "Régie"),
        ("Framework", "Marco", "Cadre"),
    ]:
        r = await client.post(
            f"/api/value-lists/{value_list['id']}/items", json={"label": tt(en, es, fr)}, headers=admin_headers
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    detail = (await client.get(f"/api/value-lists/{value_list['id']}", headers=admin_headers)).json()
    assert [i["code"] for i in detail["items"]] == ["fixed_price", "time_material", "framework"]

    order = await client.put(
        f"/api/value-lists/{value_list['id']}/order", json={"item_ids": ids[::-1]}, headers=admin_headers
    )
    assert [i["code"] for i in order.json()] == ["framework", "time_material", "fixed_price"]

    off = await client.patch(f"/api/value-list-items/{ids[0]}", json={"is_active": False}, headers=admin_headers)
    assert off.json()["is_active"] is False
    listed = {vl["code"]: vl for vl in (await client.get("/api/value-lists", headers=admin_headers)).json()}
    assert (listed["contract_type"]["item_count"], listed["contract_type"]["active_item_count"]) == (3, 2)
    actions = await audit_actions()
    assert {"value_list.created", "value_list_item.created", "value_list.reordered", "value_list_item.updated"} <= set(
        actions
    )


async def test_label_rename_keeps_code(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    value_list = await create_list(client, admin_headers)
    item = (
        await client.post(
            f"/api/value-lists/{value_list['id']}/items", json={"label": tt("Fixed price")}, headers=admin_headers
        )
    ).json()
    renamed = await client.patch(
        f"/api/value-list-items/{item['id']}", json={"label": tt("Lump sum")}, headers=admin_headers
    )
    assert (renamed.json()["code"], renamed.json()["label"]["en"]) == ("fixed_price", "Lump sum")


@pytest.mark.parametrize("role", ["editor", "viewer"])
async def test_only_admin_edits_lists(client: httpx.AsyncClient, admin_headers: dict[str, str], role: str) -> None:
    value_list = await create_list(client, admin_headers)
    await make_user(f"{role}@example.com", role)
    headers = await login(client, f"{role}@example.com")
    assert (await client.get("/api/value-lists", headers=headers)).status_code == 200
    assert (await client.get(f"/api/value-lists/{value_list['id']}", headers=headers)).status_code == 200
    for method, url, body in [
        ("POST", "/api/value-lists", {"code": "x", "name": tt("X")}),
        ("PATCH", f"/api/value-lists/{value_list['id']}", {"name": tt("Y")}),
        ("POST", f"/api/value-lists/{value_list['id']}/items", {"label": tt("Z")}),
        ("DELETE", f"/api/value-lists/{value_list['id']}", None),
    ]:
        response = await client.request(method, url, json=body, headers=headers)
        assert response.status_code == 403, (method, url)


async def test_soft_delete_and_restore(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    value_list = await create_list(client, admin_headers)
    item = (
        await client.post(f"/api/value-lists/{value_list['id']}/items", json={"label": tt("A")}, headers=admin_headers)
    ).json()
    deleted = await client.delete(f"/api/value-list-items/{item['id']}", headers=admin_headers)
    assert deleted.json()["deleted_at"] is not None
    detail = (await client.get(f"/api/value-lists/{value_list['id']}", headers=admin_headers)).json()
    assert detail["items"] == []
    trash = (
        await client.get(f"/api/value-lists/{value_list['id']}?include_deleted=true", headers=admin_headers)
    ).json()
    assert len(trash["items"]) == 1
    restored = await client.post(f"/api/value-list-items/{item['id']}/restore", headers=admin_headers)
    assert restored.json()["deleted_at"] is None


async def test_validation_and_uniqueness(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    value_list = await create_list(client, admin_headers)
    dup = await client.post(
        "/api/value-lists", json={"code": "contract_type", "name": tt("Again")}, headers=admin_headers
    )
    assert dup.json()["error"]["code"] == "value_lists.code_taken"
    bad = await client.post("/api/value-lists", json={"code": "Bad Code", "name": tt("Bad")}, headers=admin_headers)
    assert bad.json()["error"]["code"] == "value_lists.invalid_code"
    no_en = await client.post(
        "/api/value-lists", json={"code": "x", "name": {"es": "Solo español"}}, headers=admin_headers
    )
    assert no_en.status_code == 422
    await client.post(f"/api/value-lists/{value_list['id']}/items", json={"label": tt("A")}, headers=admin_headers)
    again = await client.post(
        f"/api/value-lists/{value_list['id']}/items", json={"label": tt("a")}, headers=admin_headers
    )
    assert again.json()["error"]["code"] == "value_lists.item_code_taken"


async def test_system_list_cannot_be_deleted_or_recoded(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    from tests.conftest import initial_load

    await initial_load(client, admin_headers)
    sector = next(
        vl for vl in (await client.get("/api/value-lists", headers=admin_headers)).json() if vl["code"] == "sector"
    )
    assert sector["is_system"] is True
    delete = await client.delete(f"/api/value-lists/{sector['id']}", headers=admin_headers)
    assert delete.json()["error"]["code"] == "value_lists.system_list"
    recode = await client.patch(f"/api/value-lists/{sector['id']}", json={"code": "sectors"}, headers=admin_headers)
    assert recode.json()["error"]["code"] == "value_lists.system_list"
    rename = await client.patch(
        f"/api/value-lists/{sector['id']}", json={"name": tt("Sector", "Sector", "Secteur")}, headers=admin_headers
    )
    assert rename.status_code == 200


async def test_item_in_use_must_be_deactivated(
    client: httpx.AsyncClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    value_list = await create_list(client, admin_headers)
    item = (
        await client.post(f"/api/value-lists/{value_list['id']}/items", json={"label": tt("A")}, headers=admin_headers)
    ).json()

    async def used_twice(_db: object, _item: object) -> int:
        return 2

    monkeypatch.setattr(service, "ITEM_USAGE_CHECKERS", [used_twice])
    response = await client.delete(f"/api/value-list-items/{item['id']}", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"] == {"code": "value_lists.item_in_use", "params": {"code": "a", "count": 2}}
