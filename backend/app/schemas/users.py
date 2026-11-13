import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.core.i18n import Language
from app.schemas.base import ResponseModel, StrictModel

RoleName = Literal["admin", "editor", "viewer"]


class UserCreate(StrictModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    role: RoleName
    preferred_language: Language | None = None


class UserUpdate(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: RoleName | None = None


class HardDeleteRequest(StrictModel):
    """Explicit confirmation (HR9): the admin must type the user's email."""

    confirm_email: EmailStr


class UserOut(ResponseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: RoleName
    preferred_language: Language | None
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None
    deleted_at: datetime | None


class UserWithTemporaryPassword(ResponseModel):
    user: UserOut
    temporary_password: str
