"""Functional settings: typed validation, deep merge for objects (HR10), audit of every change."""

import math
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.core.config import Settings
from app.core.errors import AppError
from app.core.i18n import SUPPORTED_LANGUAGES
from app.core.merge import deep_merge
from app.models import AppSetting
from app.repositories import settings as settings_repo
from app.schemas.settings import ClientConfig, InfrastructureItem, PublicConfig
from app.services import audit


class SettingKey:
    APP_NAME = "app.name"
    DEFAULT_LANGUAGE = "i18n.default_language"
    SESSION_HOURS = "session.duration_hours"
    LOGIN_RATE_LIMIT = "auth.login_rate_limit"
    PASSWORD_MIN_LENGTH = "auth.password_min_length"  # noqa: S105 - a setting key
    TABLE_PAGE_SIZE = "ui.table_page_size"
    MAX_IMAGE_MB = "uploads.max_image_mb"


class SettingMissingError(RuntimeError):
    """A setting the code relies on is not in the database (migrations not applied?)."""


@dataclass(frozen=True)
class SettingViolation(Exception):
    code: str
    params: dict[str, Any]


def _check(spec_type: str, constraints: dict[str, Any], value: Any, field: str | None) -> None:
    base = {"field": field} if field else {}

    def fail(code: str, **params: Any) -> None:
        raise SettingViolation(code, {**base, **params})

    if spec_type == "string":
        if not isinstance(value, str):
            fail("settings.invalid_type", expected="string")
        if len(value.strip()) < constraints.get("min_length", 0):
            fail("settings.too_short", min_length=constraints["min_length"])
        if "max_length" in constraints and len(value) > constraints["max_length"]:
            fail("settings.too_long", max_length=constraints["max_length"])
    elif spec_type in ("integer", "number"):
        is_int = isinstance(value, int) and not isinstance(value, bool)
        is_num = is_int or (isinstance(value, float) and math.isfinite(value))
        if (spec_type == "integer" and not is_int) or not is_num:
            fail("settings.invalid_type", expected=spec_type)
        if "min" in constraints and value < constraints["min"]:
            fail("settings.too_small", min=constraints["min"])
        if "max" in constraints and value > constraints["max"]:
            fail("settings.too_large", max=constraints["max"])
    elif spec_type == "boolean":
        if not isinstance(value, bool):
            fail("settings.invalid_type", expected="boolean")
    elif spec_type == "enum":
        if value not in constraints.get("options", []):
            fail("settings.invalid_option", options=constraints.get("options", []))
    elif spec_type == "object":
        if not isinstance(value, dict):
            fail("settings.invalid_type", expected="object")
        properties: dict[str, Any] = constraints.get("properties", {})
        for name in value:
            if name not in properties:
                fail("settings.unknown_field", field=name)
        for name, prop in properties.items():
            if name not in value:
                fail("settings.missing_field", field=name)
            _check(prop["type"], prop, value[name], name)
    else:
        raise SettingViolation("settings.unsupported_type", {"type": spec_type})


def validate_value(setting: AppSetting, value: Any) -> None:
    """Raise SettingViolation if `value` does not fit the setting's type and constraints."""
    _check(setting.value_type, setting.constraints or {}, value, None)


def snapshot(setting: AppSetting) -> dict[str, Any]:
    return {"value": setting.value}


async def list_settings(db: AsyncSession) -> list[AppSetting]:
    return list(await settings_repo.list_all(db))


async def update_setting(
    db: AsyncSession, key: str, raw_value: Any, *, actor: CurrentUser, request: Request | None, reset: bool = False
) -> AppSetting:
    setting = await settings_repo.get(db, key, for_update=True)
    if setting is None:
        raise AppError(404, "settings.not_found", {"key": key})
    before = snapshot(setting)
    if reset:
        new_value = setting.default_value
    elif setting.value_type == "object" and isinstance(raw_value, dict) and isinstance(setting.value, dict):
        new_value = deep_merge(setting.value, raw_value)  # HR10: partial updates keep nested keys
    else:
        new_value = raw_value
    try:
        validate_value(setting, new_value)
    except SettingViolation as violation:
        raise AppError(422, violation.code, {"key": key, **violation.params}) from None
    setting.value = new_value
    setting.updated_by = actor.id
    audit.record(
        db,
        actor=actor,
        action="settings.reset" if reset else "settings.updated",
        target_type="app_setting",
        target_id=key,
        target_label=key,
        before=before,
        after=snapshot(setting),
        request=request,
    )
    await db.commit()
    await db.refresh(setting)
    return setting


async def get_values(db: AsyncSession, *keys: str) -> dict[str, Any]:
    found = await settings_repo.values(db, keys)
    missing = [key for key in keys if key not in found]
    if missing:
        raise SettingMissingError(f"settings missing from app_settings: {', '.join(missing)}")
    return found


async def public_config(db: AsyncSession, infra: Settings) -> PublicConfig:
    values = await get_values(db, SettingKey.APP_NAME, SettingKey.DEFAULT_LANGUAGE, SettingKey.PASSWORD_MIN_LENGTH)
    return PublicConfig(
        app_name=values[SettingKey.APP_NAME],
        default_language=values[SettingKey.DEFAULT_LANGUAGE],
        auth_mode=infra.auth_mode,
        languages=list(SUPPORTED_LANGUAGES),
        password_min_length=values[SettingKey.PASSWORD_MIN_LENGTH],
    )


async def client_config(db: AsyncSession, infra: Settings) -> ClientConfig:
    values = await get_values(
        db,
        SettingKey.APP_NAME,
        SettingKey.DEFAULT_LANGUAGE,
        SettingKey.TABLE_PAGE_SIZE,
        SettingKey.MAX_IMAGE_MB,
        SettingKey.PASSWORD_MIN_LENGTH,
    )
    return ClientConfig(
        app_name=values[SettingKey.APP_NAME],
        default_language=values[SettingKey.DEFAULT_LANGUAGE],
        auth_mode=infra.auth_mode,
        languages=list(SUPPORTED_LANGUAGES),
        table_page_size=values[SettingKey.TABLE_PAGE_SIZE],
        max_image_mb=values[SettingKey.MAX_IMAGE_MB],
        password_min_length=values[SettingKey.PASSWORD_MIN_LENGTH],
    )


MASK = "••••••••"


def _mask_url_password(url: str) -> str:
    scheme, sep, rest = url.partition("://")
    if not sep or "@" not in rest:
        return url
    credentials, _, host = rest.rpartition("@")
    user, has_password, _ = credentials.partition(":")
    return f"{scheme}://{user}:{MASK}@{host}" if has_password else url


def infrastructure(infra: Settings) -> list[InfrastructureItem]:
    """Environment-only settings, read-only in the UI; secrets masked."""
    return [
        InfrastructureItem(key="ENVIRONMENT", value=infra.environment, secret=False),
        InfrastructureItem(key="DATABASE_URL", value=_mask_url_password(infra.database_url), secret=True),
        InfrastructureItem(key="AUTH_MODE", value=infra.auth_mode, secret=False),
        InfrastructureItem(key="JWT_PRIVATE_KEY_PATH", value=MASK, secret=True),
        InfrastructureItem(key="JWT_PUBLIC_KEY_PATH", value=str(infra.jwt_public_key_path.name), secret=False),
        InfrastructureItem(key="ACCESS_TOKEN_MINUTES", value=str(infra.access_token_minutes), secret=False),
        InfrastructureItem(key="CORS_ORIGINS", value=", ".join(infra.cors_origins), secret=False),
        InfrastructureItem(key="COOKIE_SECURE", value=str(infra.cookie_secure).lower(), secret=False),
        InfrastructureItem(key="LOG_LEVEL", value=infra.log_level, secret=False),
    ]
