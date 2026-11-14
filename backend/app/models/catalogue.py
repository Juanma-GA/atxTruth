"""Catalogue taxonomy: edition → blocks → families → services, plus solutions and adjacent activities.

The block of a service is always derived from its family (never stored twice). Codes are unique per
edition and type among non-deleted rows.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import IdMixin, SoftDeleteMixin, TimestampMixin
from app.schemas.translatable import TranslatableText, TranslatableTextType

ITEM_STATUSES = ("catalogue", "proposed")


def _unique_code(table: str) -> Index:
    return Index(
        f"uq_{table}_edition_code_active",
        "edition_id",
        "code",
        unique=True,
        postgresql_where=text("deleted_at IS NULL"),
    )


def _edition_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("catalogue_editions.id", ondelete="RESTRICT"), index=True)


class CatalogueEdition(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "catalogue_editions"
    __table_args__ = (
        Index("uq_catalogue_editions_code_active", "code", unique=True, postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint("status IN ('active', 'draft', 'archived')", name="status_valid"),
    )

    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    status: Mapped[str] = mapped_column(String(16))


class Block(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "blocks"
    __table_args__ = (_unique_code("blocks"),)

    edition_id: Mapped[uuid.UUID] = _edition_fk()
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    # CTO of the block, free text; empty = still to complete.
    owner: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Family(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "families"
    __table_args__ = (
        _unique_code("families"),
        CheckConstraint("status IN ('catalogue', 'proposed')", name="status_valid"),
    )

    edition_id: Mapped[uuid.UUID] = _edition_fk()
    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blocks.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    status: Mapped[str] = mapped_column(String(16), default="catalogue")
    source_ref: Mapped[str | None] = mapped_column(String(64))


class Service(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        _unique_code("services"),
        CheckConstraint("status IN ('catalogue', 'proposed')", name="status_valid"),
    )

    edition_id: Mapped[uuid.UUID] = _edition_fk()
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    status: Mapped[str] = mapped_column(String(16), default="catalogue")
    source_ref: Mapped[str | None] = mapped_column(String(64))


class Solution(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "solutions"
    __table_args__ = (_unique_code("solutions"),)

    edition_id: Mapped[uuid.UUID] = _edition_fk()
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    # A&D CCX solution types 1-4 ("1/3" in the Excel → [1, 3]).
    solution_types: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)


class AdjacentActivity(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "adjacent_activities"
    __table_args__ = (_unique_code("adjacent_activities"),)

    edition_id: Mapped[uuid.UUID] = _edition_fk()
    code: Mapped[str] = mapped_column(String(32))
    activity: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
