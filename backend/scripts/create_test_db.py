"""Create (if missing) and migrate the test database `<app db>_test`.

Usage (from backend/):  python scripts/create_test_db.py
The first time it also writes TEST_DATABASE_URL to backend/.env.
"""

import asyncio
import sys

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

import _bootstrap  # noqa: F401
from tests._testdb import BACKEND_DIR, ENV_FILE, TestDatabaseError, env_value, resolve_test_url


def _derive_test_url() -> str:
    app_url = env_value("DATABASE_URL")
    if not app_url:
        raise TestDatabaseError("DATABASE_URL is not set (backend/.env).")
    parsed = make_url(app_url)
    return parsed.set(database=f"{parsed.database}_test").render_as_string(hide_password=False)


async def _ensure_database(test_url: str) -> bool:
    parsed = make_url(test_url)
    admin_dsn = parsed.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", parsed.database)
        if exists:
            return False
        try:
            await conn.execute(f'CREATE DATABASE "{parsed.database}"')
        except asyncpg.InsufficientPrivilegeError:
            print(
                f"The role '{parsed.username}' cannot create databases. Ask an administrator to run:\n"
                f'  CREATE DATABASE "{parsed.database}" OWNER "{parsed.username}";',
                file=sys.stderr,
            )
            raise SystemExit(2) from None
        return True
    finally:
        await conn.close()


def main() -> int:
    configured = env_value("TEST_DATABASE_URL")
    test_url = configured or _derive_test_url()
    if not configured:
        with ENV_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"\nTEST_DATABASE_URL={test_url}\n")
        print(f"Added TEST_DATABASE_URL to {ENV_FILE}.")
    try:
        resolve_test_url()
    except TestDatabaseError as exc:
        print(exc, file=sys.stderr)
        return 2
    created = asyncio.run(_ensure_database(test_url))
    print("Test database created." if created else "Test database already exists.")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = test_url
    command.upgrade(config, "head")
    print("Test database migrated to head.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
