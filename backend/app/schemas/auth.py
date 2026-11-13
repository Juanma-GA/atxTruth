import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import EmailStr, Field, StringConstraints

from app.core.i18n import Language
from app.schemas.base import ResponseModel, StrictModel

Theme = Literal["system", "light", "dark"]
# Passwords are taken exactly as typed: never stripped (StrictModel strips other strings).
Password = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=200)]


class LoginRequest(StrictModel):
    email: EmailStr
    password: Password


class TokenResponse(ResponseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth token type, not a secret


class ChangePasswordRequest(StrictModel):
    current_password: Password
    new_password: Password


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
