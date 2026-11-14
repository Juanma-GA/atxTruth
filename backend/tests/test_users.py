import httpx
import pytest
from sqlalchemy import text

from app.db.base import get_sessionmaker
from tests.conftest import audit_actions, login, make_user


@pytest.mark.parametrize("role", ["viewer", "editor"])
async def test_only_admin_manages_users(client: httpx.AsyncClient, role: str) -> None:
    await make_user("someone@example.com", role)
    headers = await login(client, "someone@example.com")
    for method, url, body in (
        ("GET", "/api/users", None),
        ("POST", "/api/users", {"email": "x@example.com", "display_name": "X", "role": "viewer"}),
    ):
        response = await client.request(method, url, json=body, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "auth.forbidden"


async def test_create_user_with_temporary_password(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.post(
        "/api/users",
        json={"email": "New.Editor@example.com", "display_name": "New Editor", "role": "editor"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    temporary = body["temporary_password"]
    assert len(temporary) == 16
    assert body["user"]["email"] == "new.editor@example.com"
    assert body["user"]["must_change_password"] is True

    editor = await login(client, "new.editor@example.com", temporary)
    assert (await client.get("/api/config", headers=editor)).status_code == 403
    assert await audit_actions("new.editor@example.com") == ["user.created", "auth.login"]

    async with get_sessionmaker()() as db:
        after = (
            await db.execute(text("SELECT after::text FROM audit_events WHERE action='user.created'"))
        ).scalar_one()
    assert temporary not in after


async def test_duplicate_email_rejected(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    await make_user("ana@example.com")
    response = await client.post(
        "/api/users", json={"email": "ana@example.com", "display_name": "Ana", "role": "viewer"}, headers=admin_headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "users.email_taken"


async def test_change_role_and_guards(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    ana = await make_user("ana@example.com")
    response = await client.patch(f"/api/users/{ana.id}", json={"role": "editor"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "editor"

    me = (await client.get("/api/auth/me", headers=admin_headers)).json()
    own = await client.patch(f"/api/users/{me['id']}", json={"role": "viewer"}, headers=admin_headers)
    assert own.json()["error"]["code"] == "users.cannot_change_own_role"
    self_off = await client.post(f"/api/users/{me['id']}/deactivate", headers=admin_headers)
    assert self_off.json()["error"]["code"] == "users.cannot_deactivate_self"
    assert "user.updated" in await audit_actions("ana@example.com")


async def test_last_admin_cannot_be_demoted(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    other = await make_user("boss@example.com", "admin")
    boss = await login(client, "boss@example.com")
    me = (await client.get("/api/auth/me", headers=admin_headers)).json()
    assert (await client.patch(f"/api/users/{me['id']}", json={"role": "viewer"}, headers=boss)).status_code == 200
    last = await client.patch(f"/api/users/{other.id}", json={"role": "viewer"}, headers=admin_headers)
    assert last.status_code == 403  # admin@ is no longer admin


async def test_deactivate_restore_and_hard_delete(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    ana = await make_user("ana@example.com", "editor")
    ana_headers = await login(client, "ana@example.com")

    not_yet = await client.post(
        f"/api/users/{ana.id}/delete-permanently", json={"confirm_email": "ana@example.com"}, headers=admin_headers
    )
    assert not_yet.json()["error"]["code"] == "users.must_deactivate_first"

    off = await client.post(f"/api/users/{ana.id}/deactivate", headers=admin_headers)
    assert off.status_code == 200 and off.json()["deleted_at"] is not None
    assert (await client.get("/api/auth/me", headers=ana_headers)).status_code == 401
    listed = (await client.get("/api/users", headers=admin_headers)).json()
    assert [u["email"] for u in listed] == ["admin@example.com"]
    with_deleted = (await client.get("/api/users?include_deleted=true", headers=admin_headers)).json()
    assert len(with_deleted) == 2

    on = await client.post(f"/api/users/{ana.id}/restore", headers=admin_headers)
    assert on.json()["deleted_at"] is None
    await login(client, "ana@example.com")
    await client.post(f"/api/users/{ana.id}/deactivate", headers=admin_headers)

    mismatch = await client.post(
        f"/api/users/{ana.id}/delete-permanently", json={"confirm_email": "other@example.com"}, headers=admin_headers
    )
    assert mismatch.json()["error"]["code"] == "users.confirmation_mismatch"
    gone = await client.post(
        f"/api/users/{ana.id}/delete-permanently", json={"confirm_email": "ana@example.com"}, headers=admin_headers
    )
    assert gone.status_code == 204
    actions = await audit_actions("ana@example.com")
    assert actions[-1] == "user.deleted_permanently"
    assert "auth.login" in actions  # the trail survives the hard delete
    async with get_sessionmaker()() as db:
        orphan = await db.execute(
            text("SELECT actor_id, actor_email FROM audit_events WHERE action='auth.login' AND target_label=:e"),
            {"e": "ana@example.com"},
        )
        assert all(row.actor_id is None and row.actor_email == "ana@example.com" for row in orphan)


async def test_reset_password(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    ana = await make_user("ana@example.com")
    response = await client.post(f"/api/users/{ana.id}/reset-password", headers=admin_headers)
    temporary = response.json()["temporary_password"]
    headers = await login(client, "ana@example.com", temporary)
    assert (await client.get("/api/auth/me", headers=headers)).json()["must_change_password"] is True


async def test_unknown_user_is_404(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.patch(
        "/api/users/00000000-0000-0000-0000-000000000000", json={"role": "viewer"}, headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "users.not_found"
