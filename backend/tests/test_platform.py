"""Error contract, security headers, auth provider wiring and the test-db guard."""

import ast
from pathlib import Path

import httpx
import pytest

from app.auth.current_user import CurrentUser
from app.auth.provider import AuthModeNotImplementedError, build_auth_provider
from app.auth.roles import Role
from app.core.config import get_settings
from app.main import create_app
from tests import _testdb

BACKEND = Path(__file__).resolve().parents[1]


async def test_security_headers(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    for header in ("content-security-policy", "x-content-type-options", "x-frame-options", "referrer-policy"):
        assert header in response.headers
    assert response.headers["cache-control"] == "no-store"


async def test_unknown_route_uses_error_contract(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "http.404", "params": {}}}


async def test_unexpected_error_hides_details() -> None:
    app = create_app()

    @app.get("/api/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as http:
        response = await http.get("/api/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "server.internal"
    assert "ref" in body["error"]["params"]
    assert "secret" not in response.text


async def test_openapi_available(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "/api/auth/login" in response.json()["paths"]


async def test_cors_only_for_configured_origins(client: httpx.AsyncClient) -> None:
    allowed = await client.options(
        "/api/health", headers={"Origin": "https://test", "Access-Control-Request-Method": "GET"}
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://test"
    denied = await client.options(
        "/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in denied.headers


def test_oidc_mode_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "auth_mode", "oidc")
    with pytest.raises(AuthModeNotImplementedError, match="sso-para-it"):
        build_auth_provider()


def test_current_user_roles() -> None:
    import uuid

    user = CurrentUser(id=uuid.uuid4(), email="a@b.c", display_name="A", roles=frozenset({Role.EDITOR}))
    assert user.has_any(Role.ADMIN, Role.EDITOR)
    assert not user.has_any(Role.ADMIN)


def test_test_db_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(_testdb, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/app")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/app")
    with pytest.raises(_testdb.TestDatabaseError, match="_test"):
        _testdb.resolve_test_url()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1/app_test")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/app_test")
    with pytest.raises(_testdb.TestDatabaseError, match="application database"):
        _testdb.resolve_test_url()
    monkeypatch.delenv("TEST_DATABASE_URL")
    with pytest.raises(_testdb.TestDatabaseError, match="not set"):
        _testdb.resolve_test_url()


def _python_files() -> list[Path]:
    return [p for folder in ("app", "scripts", "tests", "alembic") for p in (BACKEND / folder).rglob("*.py")]


def test_text_files_opened_with_explicit_encoding() -> None:
    """Windows safety: every text open/read/write names its encoding."""
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in {"open", "read_text", "write_text"}:
                mode = next(
                    (a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)), ""
                )
                if "b" in str(mode):
                    continue
                if not any(k.arg == "encoding" for k in node.keywords):
                    offenders.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert offenders == []


def test_no_future_annotations_in_routes() -> None:
    routes = (BACKEND / "app" / "api" / "routes").glob("*.py")
    assert [p.name for p in routes if "from __future__ import annotations" in p.read_text(encoding="utf-8")] == []
