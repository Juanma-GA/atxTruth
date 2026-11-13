"""Development seed: an editor and a viewer with synthetic data (never in production).

Usage (from backend/):  DEV_SEED_PASSWORD=... python scripts/seed_dev_data.py
Creates editor@example.com and viewer@example.com if missing (no forced password change).
"""

import asyncio
import os
import sys

import _bootstrap  # noqa: F401
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import get_engine, get_sessionmaker
from app.models import User
from app.repositories import users as users_repo
from app.services.auth import validate_new_password

SEED_USERS = [
    ("editor@example.com", "Demo Editor", "editor"),
    ("viewer@example.com", "Demo Viewer", "viewer"),
]


async def seed(password: str) -> int:
    async with get_sessionmaker()() as db:
        await validate_new_password(db, password)
        for email, name, role in SEED_USERS:
            if await users_repo.get_by_email(db, email) is not None:
                print(f"{email} already exists.")
                continue
            users_repo.add(db, User(email=email, display_name=name, role=role, password_hash=hash_password(password)))
            print(f"{email} created ({role}).")
        await db.commit()
    await get_engine().dispose()
    return 0


def main() -> int:
    if get_settings().environment == "production":
        print("Refusing to seed development data in production.", file=sys.stderr)
        return 1
    password = os.environ.get("DEV_SEED_PASSWORD", "")
    if not password:
        print("Set DEV_SEED_PASSWORD (the password for the seeded accounts).", file=sys.stderr)
        return 2
    return asyncio.run(seed(password))


if __name__ == "__main__":
    sys.exit(main())
