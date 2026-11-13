import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.core.i18n import Language
from app.schemas.base import ResponseModel, StrictModel

Theme = Literal["system", "light", "dark"]


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(ResponseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth token type, not a secret


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class MeUpdate(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    preferred_language: Language | None = None
    theme: Theme | None = None


class MeOut(ResponseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    preferred_language: Language | None
    theme: Theme
    must_change_password: bool
    last_login_at: datetime | None
