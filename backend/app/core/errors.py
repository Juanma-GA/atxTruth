"""Error contract: the API answers `{"error": {"code": ..., "params": {...}}}`.

The frontend translates `code` (+ `params`) through i18n (HR15); the client never sees internal
details. Unexpected errors are logged with a reference id that is also returned to the client.
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("atxtruth.errors")


class AppError(Exception):
    """A business error with a stable, translatable code."""

    def __init__(self, status_code: int, code: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.params = params or {}


def error_body(code: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "params": params or {}}}


async def _app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - registered only for AppError
    headers = {"Retry-After": str(exc.params["retry_after_seconds"])} if "retry_after_seconds" in exc.params else None
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.params), headers=headers)


async def _validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    fields = [
        {"field": ".".join(str(part) for part in err.get("loc", ())[1:]) or "body", "type": str(err.get("type", ""))}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content=error_body("validation.failed", {"fields": fields}))


async def _http_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(f"http.{exc.status_code}"),
        headers=getattr(exc, "headers", None),
    )


async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
    ref = str(uuid.uuid4())
    logger.exception("unhandled_error", extra={"ref": ref, "path": request.url.path, "method": request.method})
    return JSONResponse(status_code=500, content=error_body("server.internal", {"ref": ref}))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(Exception, _unexpected_handler)
