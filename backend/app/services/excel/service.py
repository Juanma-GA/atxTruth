"""Entry points for exporting and importing a domain (used by the API routes)."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.core.errors import AppError
from app.repositories import catalogue as catalogue_repo
from app.services.audit import AuditContext
from app.services.excel import engine
from app.services.excel.domains.lists import ListsDomain
from app.services.excel.domains.taxonomy import TaxonomyDomain
from app.services.excel.report import Issue, Report
from app.services.excel.workbook import ExcelFileError, ExportMeta, read_workbook, write_workbook
from app.services.settings import SettingKey, get_values

APP_VERSION = "atxTruth 0.2.0"
DEFAULT_EDITION = "V0"
DOMAINS: dict[str, Any] = {"lists": ListsDomain(), "taxonomy": TaxonomyDomain()}
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def handler(domain: str) -> Any:
    if domain not in DOMAINS:
        raise AppError(404, "excel.unknown_domain", {"domain": domain})
    return DOMAINS[domain]


async def max_bytes(db: AsyncSession) -> int:
    megabytes = float((await get_values(db, SettingKey.MAX_EXCEL_MB))[SettingKey.MAX_EXCEL_MB])
    return int(megabytes * 1_048_576)


async def edition_or_error(db: AsyncSession, code: str) -> Any:
    found = await catalogue_repo.edition_by_code(db, code)
    if found is None:
        raise AppError(404, "catalogue.edition_not_found", {"edition": code})
    return found


async def export(db: AsyncSession, domain: str, actor: CurrentUser, edition_code: str | None) -> tuple[bytes, str]:
    h = handler(domain)
    ctx = engine.ImportContext(audit=AuditContext(actor))
    if h.spec.uses_edition:
        ctx.edition = await edition_or_error(db, edition_code or DEFAULT_EDITION)
    rows, lookups = await h.export(db, ctx)
    meta = ExportMeta(
        exported_by=actor.email, app_version=APP_VERSION, edition=ctx.edition.code if ctx.edition else None
    )
    content = write_workbook(h.spec, rows, meta, lookups)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    suffix = f"-{ctx.edition.code}" if ctx.edition else ""
    return content, f"atxtruth-{domain}{suffix}-{stamp}.xlsx"


async def finish(
    db: AsyncSession, report: Report, plans: list[tuple[Any, engine.ImportContext, list[engine.Op]]], apply: bool
) -> Report:
    if not apply:
        await db.rollback()  # Analyze never writes
        return report
    if report.has_errors:
        await db.rollback()
        raise AppError(409, "excel.has_errors", {"report": report.as_dict()})
    for h, ctx, ops in plans:
        await engine.apply(db, h, ops, ctx)
    await db.commit()
    report.applied = True
    return report


async def import_domain(
    db: AsyncSession,
    domain: str,
    content: bytes,
    file_name: str,
    actor: CurrentUser,
    request: Request | None,
    *,
    apply: bool,
    edition_code: str | None = None,
) -> Report:
    """Analyze (apply=False, writes nothing) or Apply (one transaction, all or nothing)."""
    h = handler(domain)
    report = Report(domain=domain, file_name=file_name)
    try:
        parsed = read_workbook(h.spec, content, max_bytes=await max_bytes(db), report=report)
    except ExcelFileError as exc:
        report.errors.append(exc.issue)
        if apply:
            raise AppError(409, "excel.has_errors", {"report": report.as_dict()}) from None
        return report
    audit = AuditContext(actor, request=request, source="excel", source_detail=file_name[:255])
    ctx = engine.ImportContext(audit=audit)
    if h.spec.uses_edition:
        code = str((parsed.meta or {}).get("edition") or edition_code or DEFAULT_EDITION)
        found = await catalogue_repo.edition_by_code(db, code)
        if found is None:
            report.errors.append(Issue("excel.unknown_edition", None, {"edition": code}))
            if apply:
                raise AppError(409, "excel.has_errors", {"report": report.as_dict()})
            return report
        ctx.edition = found
    ops = await engine.analyze(db, h, parsed, ctx, report)
    return await finish(db, report, [(h, ctx, ops)], apply)
