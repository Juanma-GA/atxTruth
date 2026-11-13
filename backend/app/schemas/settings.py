from datetime import datetime
from typing import Any, Literal

from app.core.i18n import Language
from app.schemas.base import ResponseModel, StrictModel
from app.schemas.translatable import TranslatableText


class SettingOut(ResponseModel):
    key: str
    category: str
    sort_order: int
    value_type: Literal["string", "integer", "number", "boolean", "enum", "object"]
    value: Any
    default_value: Any
    constraints: dict[str, Any]
    label: TranslatableText
    description: TranslatableText
    updated_at: datetime


class SettingUpdate(StrictModel):
    value: Any


class InfrastructureItem(ResponseModel):
    key: str
    value: str
    secret: bool


class PublicConfig(ResponseModel):
    app_name: str
    default_language: Language
    auth_mode: Literal["local", "oidc"]
    languages: list[Language]
    password_min_length: int


class ClientConfig(PublicConfig):
    table_page_size: int
    max_image_mb: float
