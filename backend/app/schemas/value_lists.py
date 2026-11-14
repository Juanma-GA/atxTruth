import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import ResponseModel, StrictModel
from app.schemas.translatable import TranslatableText

Code = Field(min_length=1, max_length=64)


class ValueListCreate(StrictModel):
    code: str = Code
    name: TranslatableText
    description: TranslatableText | None = None


class ValueListUpdate(StrictModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: TranslatableText | None = None
    description: TranslatableText | None = None


class ItemCreate(StrictModel):
    """`code` may be left out: it is then derived from the English label (slug)."""

    code: str | None = Field(default=None, min_length=1, max_length=64)
    label: TranslatableText
    description: TranslatableText | None = None
    is_active: bool = True


class ItemUpdate(StrictModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    label: TranslatableText | None = None
    description: TranslatableText | None = None
    is_active: bool | None = None


class ReorderRequest(StrictModel):
    item_ids: list[uuid.UUID] = Field(max_length=10000)


class ItemOut(ResponseModel):
    id: uuid.UUID
    list_id: uuid.UUID
    code: str
    label: TranslatableText
    description: TranslatableText | None
    sort_order: int
    is_active: bool
    deleted_at: datetime | None


class ValueListOut(ResponseModel):
    id: uuid.UUID
    code: str
    name: TranslatableText
    description: TranslatableText | None
    is_system: bool
    item_count: int = 0
    active_item_count: int = 0
    updated_at: datetime
    deleted_at: datetime | None


class ValueListDetail(ValueListOut):
    items: list[ItemOut]
