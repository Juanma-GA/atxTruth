import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """An account. Deactivating sets `deleted_at` (soft delete, HR9)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name="role_valid"),
        CheckConstraint("preferred_language IS NULL OR preferred_language IN ('en', 'es', 'fr')", name="language"),
        CheckConstraint("theme IN ('system', 'light', 'dark')", name="theme_valid"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        Index("uq_users_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(200))
    # NULL for identities that come from an external IdP (AUTH_MODE=oidc).
    password_hash: Mapped[str | None] = mapped_column(String(200))
    external_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    preferred_language: Mapped[str | None] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(8), default="system", server_default="system")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
