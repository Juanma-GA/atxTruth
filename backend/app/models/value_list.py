import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin, SoftDeleteMixin, TimestampMixin
from app.schemas.translatable import TranslatableText, TranslatableTextType


class ValueList(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An editable list of values (sectors, IQP, review statuses...). Code is stable."""

    __tablename__ = "value_lists"
    __table_args__ = (
        Index("uq_value_lists_code_active", "code", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )

    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    description: Mapped[TranslatableText | None] = mapped_column(TranslatableTextType())
    # System lists back fields of the app: they cannot be deleted nor change code.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    items: Mapped[list["ValueListItem"]] = relationship(back_populates="value_list", lazy="raise")


class ValueListItem(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "value_list_items"
    __table_args__ = (
        Index(
            "uq_value_list_items_list_code_active",
            "list_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("value_lists.id", ondelete="CASCADE"), index=True
    )
    # Stable within its list: renaming the label never changes it.
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[TranslatableText] = mapped_column(TranslatableTextType())
    description: Mapped[TranslatableText | None] = mapped_column(TranslatableTextType())
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    value_list: Mapped[ValueList] = relationship(back_populates="items", lazy="raise")

    def snapshot(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label.to_db(),
            "description": self.description.to_db() if self.description else None,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }
