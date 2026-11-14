"""Excel round trip. Exporting is open to every signed-in user (viewers "consult and generate");
importing is admin-only. Analyze never writes; Apply re-analyses the same file inside one
transaction and writes everything or nothing."""

from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.deps import get_current_user, require_admin
from app.core.errors import AppError
from app.db.base import get_db
from app.services.excel import initial_load
from app.services.excel import service as excel

router = APIRouter(tags=["excel"])
XLSX_SUFFIX = ".xlsx"


async def _read_upload(db: AsyncSession, upload: UploadFile) -> tuple[bytes, str]:
    name = (upload.filename or "upload.xlsx").replace("\\", "/").rsplit("/", 1)[-1]
    if not name.lower().endswith(XLSX_SUFFIX):
        raise AppError(422, "excel.not_xlsx")
    limit = await excel.max_bytes(db)
    content = await upload.read(limit + 1)
    if len(content) > limit:
        raise AppError(413, "excel.too_large", {"max_mb": round(limit / 1_048_576, 1)})
    return content, name


@router.get("/api/excel/{domain}/export")
async def export(
    domain: str,
    edition: str | None = Query(default=None, max_length=32),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content, filename = await excel.export(db, domain, user, edition)
    return Response(
        content=content,
        media_type=excel.XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/excel/{domain}/analyze")
async def analyze(
    domain: str,
    request: Request,
    file: UploadFile = File(...),
    edition: str | None = Query(default=None, max_length=32),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    content, name = await _read_upload(db, file)
    report = await excel.import_domain(db, domain, content, name, admin, request, apply=False, edition_code=edition)
    return report.as_dict()


@router.post("/api/excel/{domain}/apply")
async def apply(
    domain: str,
    request: Request,
    file: UploadFile = File(...),
    edition: str | None = Query(default=None, max_length=32),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    content, name = await _read_upload(db, file)
    report = await excel.import_domain(db, domain, content, name, admin, request, apply=True, edition_code=edition)
    return report.as_dict()


@router.post("/api/initial-load/analyze")
async def initial_analyze(
    request: Request,
    file: UploadFile = File(...),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    content, name = await _read_upload(db, file)
    return (await initial_load.run(db, content, name, admin, request, apply=False)).as_dict()


@router.post("/api/initial-load/apply")
async def initial_apply(
    request: Request,
    file: UploadFile = File(...),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    content, name = await _read_upload(db, file)
    return (await initial_load.run(db, content, name, admin, request, apply=True)).as_dict()
