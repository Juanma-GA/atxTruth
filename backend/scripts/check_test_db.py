"""One-line check that the test database answers and is at the latest migration.

Exit codes: 0 ready, 2 missing/unreachable/not migrated (an environment problem, not an app failure).
"""

import asyncio
import sys

import asyncpg
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

import _bootstrap  # noqa: F401
from tests._testdb import BACKEND_DIR, TestDatabaseError, resolve_test_url


async def _current(url: str) -> str | None:
    dsn = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    conn = await asyncpg.connect(dsn)
    try:
        value: str | None = await conn.fetchval("SELECT version_num FROM alembic_version")
        return value
    except asyncpg.UndefinedTableError:
        return None
    finally:
        await conn.close()


def main() -> int:
    try:
        url = resolve_test_url()
    except TestDatabaseError as exc:
        print(f"test db: {exc}")
        return 2
    head = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_current_head()
    try:
        current = asyncio.run(_current(url))
    except (OSError, asyncpg.PostgresError) as exc:
        print(f"test db: cannot connect ({type(exc).__name__}). Is Postgres running? `npm run test:db:create`")
        return 2
    if current != head:
        print(f"test db: at {current}, head is {head}. Run `npm run test:db:create`.")
        return 2
    print(f"test db: ready ({make_url(url).database} at {head})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
