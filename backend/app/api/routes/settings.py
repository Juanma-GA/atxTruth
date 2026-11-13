"""Functional settings (admin) and the configuration the frontend needs."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.db.base import get_db
from app.schemas.settings import ClientConfig, InfrastructureItem, PublicConfig, SettingOut, SettingUpdate
from app.services import settings as settings_service

router = APIRouter(tags=["settings"])


@router.get("/api/public/config", response_model=PublicConfig)
async def public_config(db: AsyncSession = Depends(get_db)) -> PublicConfig:
    """What the login screen needs: app name, default language, auth mode."""
    return await settings_service.public_config(db, get_settings())


@router.get("/api/config", response_model=ClientConfig)
async def client_config(
    _user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ClientConfig:
    return await settings_service.client_config(db, get_settings())


@router.get("/api/settings", response_model=list[SettingOut])
async def list_settings(
    _admin: CurrentUser = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> list[SettingOut]:
    return [SettingOut.model_validate(s) for s in await settings_service.list_settings(db)]


@router.get("/api/settings/infrastructure", response_model=list[InfrastructureItem])
async def infrastructure(_admin: CurrentUser = Depends(require_admin)) -> list[InfrastructureItem]:
    return settings_service.infrastructure(get_settings())


@router.patch("/api/settings/{key}", response_model=SettingOut)
async def update_setting(
    key: str,
    body: SettingUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SettingOut:
    setting = await settings_service.update_setting(db, key, body.value, actor=admin, request=request)
    return SettingOut.model_validate(setting)


@router.post("/api/settings/{key}/reset", response_model=SettingOut)
async def reset_setting(
    key: str, request: Request, admin: CurrentUser = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> SettingOut:
    setting = await settings_service.update_setting(db, key, None, actor=admin, request=request, reset=True)
    return SettingOut.model_validate(setting)
