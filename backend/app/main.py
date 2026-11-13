"""atxTruth API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, auth, health, settings, users
from app.auth.provider import build_auth_provider
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import install_middleware


def create_app() -> FastAPI:
    infra = get_settings()
    configure_logging(infra.log_level)
    app = FastAPI(
        title="atxTruth API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.auth_provider = build_auth_provider()
    register_error_handlers(app)
    install_middleware(app, hsts=infra.environment == "production")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=infra.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(settings.router)
    app.include_router(audit.router)
    if infra.auth_mode == "local":
        app.include_router(auth.local_router)
        app.include_router(users.router)
    return app


app = create_app()
