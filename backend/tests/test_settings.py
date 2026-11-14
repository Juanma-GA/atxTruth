from typing import Any

import httpx
import pytest
from sqlalchemy import text

from app.core.merge import deep_merge
from app.db.base import get_sessionmaker
from app.models import AppSetting
from app.services.settings import SettingViolation, _mask_url_password, validate_value
from tests.conftest import login, make_user


async def test_viewer_cannot_read_or_change_settings(client: httpx.AsyncClient) -> None:
    await make_user("viewer@example.com", "viewer")
    headers = await login(client, "viewer@example.com")
    assert (await client.get("/api/settings", headers=headers)).status_code == 403
    assert (await client.get("/api/settings/infrastructure", headers=headers)).status_code == 403
    patch = await client.patch("/api/settings/ui.table_page_size", json={"value": 50}, headers=headers)
    assert patch.status_code == 403
    config = await client.get("/api/config", headers=headers)
    assert config.status_code == 200
    assert config.json()["table_page_size"] == 25


async def test_seeded_settings(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    settings = (await client.get("/api/settings", headers=admin_headers)).json()
    keys = {s["key"] for s in settings}
    assert {
        "app.name",
        "i18n.default_language",
        "session.duration_hours",
        "ui.table_page_size",
        "uploads.max_image_mb",
        "auth.login_rate_limit",
        "auth.password_min_length",
    } <= keys
    for setting in settings:
        assert set(setting["label"]) == {"en", "es", "fr"}
        assert all(setting["label"].values()) and all(setting["description"].values())


async def test_update_is_validated_persisted_and_audited(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.patch("/api/settings/ui.table_page_size", json={"value": 50}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["value"] == 50
    assert (await client.get("/api/config", headers=admin_headers)).json()["table_page_size"] == 50

    async with get_sessionmaker()() as db:
        row = (
            await db.execute(
                text("SELECT actor_email, before, after FROM audit_events WHERE action='settings.updated'")
            )
        ).one()
    assert row.actor_email == "admin@example.com"
    assert (row.before, row.after) == ({"value": 25}, {"value": 50})

    too_big = await client.patch("/api/settings/ui.table_page_size", json={"value": 1000}, headers=admin_headers)
    assert too_big.status_code == 422
    assert too_big.json()["error"] == {
        "code": "settings.too_large",
        "params": {"key": "ui.table_page_size", "max": 200},
    }
    wrong_type = await client.patch("/api/settings/ui.table_page_size", json={"value": "50"}, headers=admin_headers)
    assert wrong_type.json()["error"]["code"] == "settings.invalid_type"
    unknown = await client.patch("/api/settings/nope", json={"value": 1}, headers=admin_headers)
    assert unknown.status_code == 404


async def test_object_setting_is_deep_merged(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    response = await client.patch(
        "/api/settings/auth.login_rate_limit", json={"value": {"max_attempts": 3}}, headers=admin_headers
    )
    assert response.json()["value"] == {"max_attempts": 3, "window_minutes": 15}
    bad = await client.patch("/api/settings/auth.login_rate_limit", json={"value": {"bogus": 1}}, headers=admin_headers)
    assert bad.json()["error"]["code"] == "settings.unknown_field"
    out_of_range = await client.patch(
        "/api/settings/auth.login_rate_limit", json={"value": {"window_minutes": 0}}, headers=admin_headers
    )
    assert out_of_range.json()["error"]["params"] == {
        "key": "auth.login_rate_limit",
        "field": "window_minutes",
        "min": 1,
    }


async def test_reset_restores_default(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    await client.patch("/api/settings/app.name", json={"value": "Truth"}, headers=admin_headers)
    assert (await client.get("/api/public/config")).json()["app_name"] == "Truth"
    reset = await client.post("/api/settings/app.name/reset", headers=admin_headers)
    assert reset.json()["value"] == "atxTruth"


async def test_public_config_needs_no_login(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/public/config")).json()
    assert body == {
        "app_name": "atxTruth",
        "default_language": "en",
        "auth_mode": "local",
        "languages": ["en", "es", "fr"],
        "password_min_length": 12,
    }


async def test_infrastructure_is_masked(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> None:
    items = {i["key"]: i for i in (await client.get("/api/settings/infrastructure", headers=admin_headers)).json()}
    assert ":••••••••@" in items["DATABASE_URL"]["value"]
    assert items["DATABASE_URL"]["secret"] is True
    assert items["JWT_PRIVATE_KEY_PATH"]["value"] == "••••••••"


def test_mask_url_password() -> None:
    url = "postgresql://u:secret@h:5432/db"  # pragma: allowlist secret
    assert _mask_url_password(url) == "postgresql://u:••••••••@h:5432/db"
    assert _mask_url_password("postgresql://h/db") == "postgresql://h/db"


def test_deep_merge_keeps_nested_keys_and_does_not_mutate() -> None:
    base: dict[str, Any] = {"a": {"b": 1, "c": {"d": 2, "e": 3}}, "f": 4}
    merged = deep_merge(base, {"a": {"c": {"d": 9}}})
    assert merged == {"a": {"b": 1, "c": {"d": 9, "e": 3}}, "f": 4}
    assert base["a"]["c"]["d"] == 2


@pytest.mark.parametrize(
    ("value_type", "constraints", "value", "code"),
    [
        ("integer", {"min": 1}, True, "settings.invalid_type"),
        ("integer", {"min": 1}, 1.5, "settings.invalid_type"),
        ("number", {"max": 5}, 5.5, "settings.too_large"),
        ("number", {}, float("nan"), "settings.invalid_type"),
        ("string", {"min_length": 1}, "   ", "settings.too_short"),
        ("string", {"max_length": 3}, "abcd", "settings.too_long"),
        ("enum", {"options": ["en"]}, "de", "settings.invalid_option"),
        ("boolean", {}, "true", "settings.invalid_type"),
        ("object", {"properties": {"a": {"type": "integer"}}}, {}, "settings.missing_field"),
    ],
)
def test_validation_rejects(value_type: str, constraints: dict[str, Any], value: Any, code: str) -> None:
    setting = AppSetting(key="k", value_type=value_type, constraints=constraints)
    with pytest.raises(SettingViolation) as caught:
        validate_value(setting, value)
    assert caught.value.code == code


def test_validation_accepts_valid_values() -> None:
    validate_value(AppSetting(key="k", value_type="number", constraints={"min": 0.1}), 2)
    validate_value(AppSetting(key="k", value_type="boolean", constraints={}), False)
