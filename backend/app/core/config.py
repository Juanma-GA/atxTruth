"""Infrastructure settings, read only from the environment (or backend/.env).

Only infrastructure and secrets live here (database, JWT keys, CORS, auth mode).
Functional settings (app name, default language, session length, page size...) live in
Postgres (`app_settings`) and are edited from the admin UI (HR0/HR8).
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = Field(min_length=1)
    auth_mode: Literal["local", "oidc"] = "local"
    jwt_private_key_path: Path = Path("keys/jwt_private.pem")
    jwt_public_key_path: Path = Path("keys/jwt_public.pem")
    access_token_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_reuse_grace_seconds: int = Field(default=10, ge=0, le=120)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    cookie_secure: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("jwt_private_key_path", "jwt_public_key_path")
    @classmethod
    def _resolve_key_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_DIR / value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
