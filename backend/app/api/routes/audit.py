from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import require_admin
from app.db.base import get_db
from app.repositories import audit as audit_repo
from app.schemas.audit import AuditEventOut, AuditPage

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
async def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    action: str | None = Query(default=None, max_length=200),
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AuditPage:
    items, total = await audit_repo.page(db, offset=(page - 1) * page_size, limit=page_size, action_prefix=action)
    return AuditPage(
        items=[AuditEventOut.model_validate(e) for e in items], total=total, page=page, page_size=page_size
    )
