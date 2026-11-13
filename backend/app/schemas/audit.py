import uuid
from datetime import datetime
from typing import Any

from app.schemas.base import ResponseModel


class AuditEventOut(ResponseModel):
    id: uuid.UUID
    occurred_at: datetime
    actor_email: str | None
    action: str
    target_type: str
    target_id: str | None
    target_label: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class AuditPage(ResponseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int
