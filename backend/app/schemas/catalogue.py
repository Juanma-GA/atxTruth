import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ResponseModel, StrictModel
from app.schemas.translatable import TranslatableText

Status = Literal["catalogue", "proposed"]


class CatalogueCreate(StrictModel):
    """Fields that do not apply to the kind are rejected (catalogue.field_not_allowed)."""

    code: str = Field(min_length=1, max_length=32)
    name: TranslatableText
    owner: str | None = Field(default=None, max_length=200)
    sort_order: int | None = Field(default=None, ge=0, le=1_000_000)
    block_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None
    status: Status | None = None
    source_ref: str | None = Field(default=None, max_length=64)
    solution_types: list[int] | None = Field(default=None, max_length=4)


class CatalogueUpdate(StrictModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    # Changing a code needs explicit confirmation: a previously exported Excel no longer matches it.
    confirm_code_change: bool = False
    name: TranslatableText | None = None
    owner: str | None = Field(default=None, max_length=200)
    sort_order: int | None = Field(default=None, ge=0, le=1_000_000)
    block_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None
    status: Status | None = None
    source_ref: str | None = Field(default=None, max_length=64)
    solution_types: list[int] | None = Field(default=None, max_length=4)


class CatalogueItemOut(ResponseModel):
    id: uuid.UUID
    kind: str
    code: str
    name: TranslatableText
    owner: str | None = None
    sort_order: int | None = None
    status: Status | None = None
    source_ref: str | None = None
    solution_types: list[int] | None = None
    block_id: uuid.UUID | None = None
    family_id: uuid.UUID | None = None
    deleted_at: datetime | None
    updated_at: datetime


class ServiceNode(CatalogueItemOut):
    pass


class FamilyNode(CatalogueItemOut):
    services: list[ServiceNode]


class BlockNode(CatalogueItemOut):
    families: list[FamilyNode]


class EditionOut(ResponseModel):
    id: uuid.UUID
    code: str
    name: TranslatableText
    status: str


class CatalogueTree(ResponseModel):
    edition: EditionOut
    blocks: list[BlockNode]
    solutions: list[CatalogueItemOut]
    adjacent: list[CatalogueItemOut]


class HistoryEvent(ResponseModel):
    id: uuid.UUID
    occurred_at: datetime
    actor_email: str | None
    action: str
    source: str
    source_detail: str | None
    before: dict[str, object] | None
    after: dict[str, object] | None
