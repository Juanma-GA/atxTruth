from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import get_sessionmaker
from tests.conftest import DEFAULT_PASSWORD, audit_actions, login, make_user

COOKIE = "atx_refresh"


def _use_cookie(client: httpx.AsyncClient, value: str | None) -> None:
    """Replace the jar with exactly this refresh cookie (simulates another tab / a stolen copy)."""
    assert value is not None
    client.cookies.clear()
    client.cookies.set(COOKIE, value)


def _cookie_header(response: httpx.Response) -> str:
    return response.headers["set-cookie"]


async def test_login_sets_secure_httponly_strict_cookie_and_audits(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com", "editor")
    response = await client.post("/api/auth/login", json={"email": "Ana@Example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    assert response.json()["access_token"]
    cookie = _cookie_header(response).lower()
    for flag in ("httponly", "secure", "samesite=strict", "path=/api/auth"):
        assert flag in cookie
    assert await audit_actions("ana@example.com") == ["auth.login"]


async def test_bad_credentials_same_answer_and_audited(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    bad_password = "nope"  # pragma: allowlist secret
    wrong = await client.post("/api/auth/login", json={"email": "ana@example.com", "password": bad_password})
    unknown = await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": bad_password})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"error": {"code": "auth.invalid_credentials", "params": {}}}
    assert await audit_actions("ana@example.com") == ["auth.login_failed"]


async def test_login_rate_limit_uses_setting(client: httpx.AsyncClient) -> None:
    await make_user("admin@example.com", "admin")
    headers = await login(client, "admin@example.com")
    patch = await client.patch(
        "/api/settings/auth.login_rate_limit", json={"value": {"max_attempts": 2}}, headers=headers
    )
    assert patch.status_code == 200
    await make_user("ana@example.com")
    for _ in range(2):
        assert (
            await client.post("/api/auth/login", json={"email": "ana@example.com", "password": "x"})
        ).status_code == 401
    blocked = await client.post("/api/auth/login", json={"email": "ana@example.com", "password": DEFAULT_PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "auth.too_many_attempts"
    assert blocked.json()["error"]["params"]["minutes"] == 15
    assert blocked.headers["retry-after"] == "900"


async def test_successful_login_resets_failure_count(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    for _ in range(4):
        await client.post("/api/auth/login", json={"email": "ana@example.com", "password": "x"})
    await login(client, "ana@example.com")
    for _ in range(4):
        await client.post("/api/auth/login", json={"email": "ana@example.com", "password": "x"})
    await login(client, "ana@example.com")  # 4 failures since the last success: still under 5


async def test_deactivated_user_cannot_login(client: httpx.AsyncClient) -> None:
    user = await make_user("ana@example.com")
    async with get_sessionmaker()() as db:
        await db.execute(text("UPDATE users SET deleted_at = now() WHERE id = :id"), {"id": user.id})
        await db.commit()
    response = await client.post("/api/auth/login", json={"email": "ana@example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 401


async def test_refresh_rotates_and_logout_revokes(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    await login(client, "ana@example.com")
    first = client.cookies.get(COOKIE)
    refreshed = await client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    second = client.cookies.get(COOKIE)
    assert second and second != first
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"})
    assert me.json()["email"] == "ana@example.com"

    assert (await client.post("/api/auth/logout")).status_code == 204
    _use_cookie(client, second)
    after = await client.post("/api/auth/refresh")
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "auth.session_expired"


async def test_refresh_reuse_after_grace_ends_every_session(client: httpx.AsyncClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "refresh_token_reuse_grace_seconds", 0)
    await make_user("ana@example.com")
    await login(client, "ana@example.com")
    stolen = client.cookies.get(COOKIE)
    assert (await client.post("/api/auth/refresh")).status_code == 200
    async with get_sessionmaker()() as db:
        await db.execute(
            text("UPDATE refresh_tokens SET rotated_at = :t, revoked_at = :t WHERE rotated_at IS NOT NULL"),
            {"t": datetime.now(UTC) - timedelta(seconds=5)},
        )
        await db.commit()
    current = client.cookies.get(COOKIE)
    _use_cookie(client, stolen)
    assert (await client.post("/api/auth/refresh")).status_code == 401
    _use_cookie(client, current)
    assert (await client.post("/api/auth/refresh")).status_code == 401  # the legitimate session was ended too
    assert "auth.refresh_reuse_detected" in await audit_actions()


async def test_refresh_within_grace_keeps_session(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    await login(client, "ana@example.com")
    old = client.cookies.get(COOKIE)
    assert (await client.post("/api/auth/refresh")).status_code == 200
    _use_cookie(client, old)
    assert (await client.post("/api/auth/refresh")).status_code == 200


async def test_session_duration_comes_from_settings(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    response = await client.post("/api/auth/login", json={"email": "ana@example.com", "password": DEFAULT_PASSWORD})
    assert "max-age=43200" in _cookie_header(response).lower()  # 12 h default


async def test_cross_origin_cookie_requests_rejected(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    response = await client.post(
        "/api/auth/login",
        json={"email": "ana@example.com", "password": DEFAULT_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "auth.origin_not_allowed"


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.not_authenticated"
    bad = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


async def test_preferences_are_stored_on_the_account(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    headers = await login(client, "ana@example.com")
    response = await client.patch("/api/auth/me", json={"preferred_language": "fr", "theme": "dark"}, headers=headers)
    assert response.status_code == 200
    headers = await login(client, "ana@example.com")
    me = (await client.get("/api/auth/me", headers=headers)).json()
    assert (me["preferred_language"], me["theme"]) == ("fr", "dark")
    assert "account.updated" in await audit_actions("ana@example.com")
    cleared = await client.patch("/api/auth/me", json={"preferred_language": None}, headers=headers)
    assert cleared.json()["preferred_language"] is None
    null_theme = await client.patch("/api/auth/me", json={"theme": None}, headers=headers)
    assert null_theme.status_code == 422
    invalid = await client.patch("/api/auth/me", json={"preferred_language": "de"}, headers=headers)
    assert invalid.status_code == 422
    extra = await client.patch("/api/auth/me", json={"role": "admin"}, headers=headers)
    assert extra.status_code == 422
    assert extra.json()["error"]["params"]["fields"][0] == {"field": "role", "type": "extra_forbidden"}


async def test_forced_password_change(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com", must_change_password=True)
    headers = await login(client, "ana@example.com")
    assert (await client.get("/api/auth/me", headers=headers)).json()["must_change_password"] is True
    blocked = await client.get("/api/config", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "auth.password_change_required"

    short = await client.post(
        "/api/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "short"},  # pragma: allowlist secret
        headers=headers,
    )
    assert short.status_code == 422
    assert short.json()["error"] == {"code": "auth.password_too_short", "params": {"min": 12}}
    wrong = await client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "AnotherLongPass1"},  # pragma: allowlist secret
        headers=headers,
    )
    assert wrong.status_code == 403
    same = await client.post(
        "/api/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD},
        headers=headers,
    )
    assert same.json()["error"]["code"] == "auth.password_unchanged"
    ok = await client.post(
        "/api/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "AnotherLongPass1"},  # pragma: allowlist secret
        headers=headers,
    )
    assert ok.status_code == 204
    assert (await client.get("/api/config", headers=headers)).status_code == 200
    await login(client, "ana@example.com", "AnotherLongPass1")
    assert "auth.password_changed" in await audit_actions("ana@example.com")


async def test_password_change_ends_other_sessions(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    await login(client, "ana@example.com")
    other_session = client.cookies.get(COOKIE)
    headers = await login(client, "ana@example.com")
    mine = client.cookies.get(COOKIE)
    await client.post(
        "/api/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "AnotherLongPass1"},  # pragma: allowlist secret
        headers=headers,
    )
    _use_cookie(client, other_session)
    assert (await client.post("/api/auth/refresh")).status_code == 401
    _use_cookie(client, mine)
    assert (await client.post("/api/auth/refresh")).status_code == 200


async def test_no_passwords_or_tokens_in_audit(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com")
    await login(client, "ana@example.com")
    async with get_sessionmaker()() as db:
        dump = (await db.execute(text("SELECT coalesce(json_agg(a)::text, '') FROM audit_events a"))).scalar_one()
    assert DEFAULT_PASSWORD not in dump
    assert "password_hash" not in dump
    assert client.cookies.get(COOKIE) not in dump


async def test_rate_limit_holds_under_concurrent_attempts(client: httpx.AsyncClient) -> None:
    import asyncio

    await make_user("ana@example.com")
    responses = await asyncio.gather(
        *(client.post("/api/auth/login", json={"email": "ana@example.com", "password": "x"}) for _ in range(8))
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses.count(401) == 5  # max_attempts
    assert statuses.count(429) == 3


async def test_passwords_are_not_stripped(client: httpx.AsyncClient) -> None:
    await make_user("ana@example.com", password=" spaced pass 1 ")
    stripped = "spaced pass 1"  # pragma: allowlist secret
    bad = await client.post("/api/auth/login", json={"email": "ana@example.com", "password": stripped})
    assert bad.status_code == 401
    await login(client, "ana@example.com", " spaced pass 1 ")
