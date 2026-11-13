"""Security headers and request logging."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("atxtruth.http")

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Swagger UI / ReDoc load their bundle from jsDelivr (FastAPI default).
DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
    "worker-src 'self' blob:; frame-ancestors 'none'"
)
DOCS_PATHS = ("/api/docs", "/api/redoc")


def install_middleware(app: FastAPI, *, hsts: bool) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        path = request.url.path
        response.headers["Content-Security-Policy"] = DOCS_CSP if path.startswith(DOCS_PATHS) else API_CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["X-Request-ID"] = request_id
        if path.startswith("/api/") and not path.startswith(DOCS_PATHS):
            response.headers["Cache-Control"] = "no-store"
        if hsts:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response
