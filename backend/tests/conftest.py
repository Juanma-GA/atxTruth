"""Test setup: a real Postgres test database (never the app's), migrated, cleaned per test."""

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from tests._testdb import BACKEND_DIR, TestDatabaseError, resolve_test_url

try:
    _TEST_URL = resolve_test_url()
except TestDatabaseError as _exc:
    pytest.exit(f"test db: {_exc}", returncode=2)

# Everything the app reads from the environment is pinned before it is imported.
os.environ["DATABASE_URL"] = _TEST_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_MODE"] = "local"
os.environ["CORS_ORIGINS"] = "https://test"
os.environ["COOKIE_SECURE"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"

_KEYS_DIR = Path(tempfile.mkdtemp(prefix="atxtruth-test-keys-"))


def _write_keys() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (_KEYS_DIR / "private.pem").write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    (_KEYS_DIR / "public.pem").write_bytes(
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )


_write_keys()
os.environ["JWT_PRIVATE_KEY_PATH"] = str(_KEYS_DIR / "private.pem")
os.environ["JWT_PUBLIC_KEY_PATH"] = str(_KEYS_DIR / "public.pem")


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = _TEST_URL
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


_migrate()

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import get_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402

DEFAULT_PASSWORD = "CorrectHorse123!"


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    async with get_sessionmaker()() as db:
        # Not TRUNCATE ... CASCADE: app_settings references users and must keep its rows.
        await db.execute(text("UPDATE app_settings SET value = default_value, updated_by = NULL"))
        await db.execute(text("DELETE FROM audit_events"))
        await db.execute(text("DELETE FROM refresh_tokens"))
        await db.execute(text("DELETE FROM users"))
        await db.commit()
    yield


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as http:
        yield http


async def make_user(
    email: str,
    role: str = "viewer",
    *,
    password: str = DEFAULT_PASSWORD,
    must_change_password: bool = False,
) -> User:
    async with get_sessionmaker()() as session:
        user = User(
            email=email,
            display_name=email.split("@")[0].title(),
            role=role,
            password_hash=hash_password(password),
            must_change_password=must_change_password,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login(http: httpx.AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> dict[str, str]:
    response = await http.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def audit_actions(target_label: str | None = None) -> list[str]:
    async with get_sessionmaker()() as session:
        query = "SELECT action FROM audit_events"
        params: dict[str, str] = {}
        if target_label is not None:
            query += " WHERE target_label = :label"
            params["label"] = target_label
        rows = await session.execute(text(query + " ORDER BY occurred_at"), params)
        return [row[0] for row in rows]
