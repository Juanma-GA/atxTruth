"""Rules for the test database: its own database, name ending in `_test`, never the app's.

Shared by tests/conftest.py and scripts/create_test_db.py / check_test_db.py.
"""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


class TestDatabaseError(RuntimeError):
    """The test database is not configured safely."""


def env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if ENV_FILE.is_file():
        file_value = dotenv_values(ENV_FILE, encoding="utf-8").get(name)
        return file_value or None
    return None


def _same_server(a: str | None, b: str | None) -> bool:
    local = {"localhost", "127.0.0.1", "::1", None}
    return a == b or (a in local and b in local)


def resolve_test_url() -> str:
    test_url = env_value("TEST_DATABASE_URL")
    if not test_url:
        raise TestDatabaseError(
            "TEST_DATABASE_URL is not set. Run `npm run test:db:create` (or backend/scripts/create_test_db.py)."
        )
    parsed = make_url(test_url)
    if not (parsed.database or "").endswith("_test"):
        raise TestDatabaseError(f"TEST_DATABASE_URL database must end in '_test' (got '{parsed.database}').")
    app_url = env_value("DATABASE_URL")
    if app_url:
        app = make_url(app_url)
        if (
            app.database == parsed.database
            and _same_server(app.host, parsed.host)
            and (app.port or 5432) == (parsed.port or 5432)
        ):
            raise TestDatabaseError("TEST_DATABASE_URL points at the application database; refusing to run tests.")
    return test_url
