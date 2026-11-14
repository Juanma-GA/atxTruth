"""Audit trail (AACF Rule 4). Events are written in the same transaction as the change."""

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.models import AuditEvent
from app.repositories import audit as audit_repo

# Never stored in before/after snapshots, whatever the caller passes.
_FORBIDDEN_KEYS = {"password", "password_hash", "token", "token_hash", "access_token", "refresh_token"}


def _clean(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {k: _clean(v) if isinstance(v, dict) else v for k, v in snapshot.items() if k not in _FORBIDDEN_KEYS}


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def record(
    db: AsyncSession,
    *,
    actor: CurrentUser | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    target_label: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request: Request | None = None,
    source: str = "ui",
    source_detail: str | None = None,
) -> None:
    audit_repo.add(
        db,
        AuditEvent(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            before=_clean(before),
            after=_clean(after),
            ip=client_ip(request),
            source=source,
            source_detail=source_detail,
        ),
    )


class AuditContext:
    """Who is changing data and from where: passed down to every business operation."""

    def __init__(
        self,
        actor: CurrentUser | None,
        *,
        request: Request | None = None,
        source: str = "ui",
        source_detail: str | None = None,
    ) -> None:
        self.actor = actor
        self.request = request
        self.source = source
        self.source_detail = source_detail

    def record(
        self,
        db: AsyncSession,
        *,
        action: str,
        target_type: str,
        target_id: str | None,
        target_label: str | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        record(
            db,
            actor=self.actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            before=before,
            after=after,
            request=self.request,
            source=self.source,
            source_detail=self.source_detail,
        )
