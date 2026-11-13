import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """Who did what, when, on what, with before/after snapshots (AACF Rule 4).

    Never stores passwords or tokens. `actor_email` is a snapshot so the trail survives a hard
    delete of the user (actor_id is then set to NULL).
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_action_label_time", "action", "target_label", "occurred_at"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    actor_email: Mapped[str | None] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    target_label: Mapped[str | None] = mapped_column(String(320))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
