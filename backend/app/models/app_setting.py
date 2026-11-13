import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSetting(Base):
    """A functional setting edited from Settings → Configuration (HR0/HR8).

    `value_type` + `constraints` drive validation; `label`/`description` are TranslatableText.
    """

    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint(
            "value_type IN ('string', 'integer', 'number', 'boolean', 'enum', 'object')", name="value_type_valid"
        ),
    )

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[str] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    value_type: Mapped[str] = mapped_column(String(16))
    value: Mapped[Any] = mapped_column(JSONB)
    default_value: Mapped[Any] = mapped_column(JSONB)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    label: Mapped[dict[str, Any]] = mapped_column(JSONB)
    description: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
