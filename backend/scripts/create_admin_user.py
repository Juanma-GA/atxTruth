"""Create the initial admin from INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD (AUTH_MODE=local).

Usage (from backend/):  python scripts/create_admin_user.py
Does nothing if a user with that email already exists.
"""

import asyncio
import os
import sys

import _bootstrap  # noqa: F401
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.base import get_engine, get_sessionmaker
from app.models import User
from app.repositories import users as users_repo
from app.services import audit
from app.services.auth import validate_new_password
from app.services.users import snapshot


async def create(email: str, password: str) -> int:
    async with get_sessionmaker()() as db:
        if await users_repo.get_by_email(db, email) is not None:
            print(f"A user with email {email} already exists; nothing to do.")
            return 0
        try:
            await validate_new_password(db, password)
        except AppError as exc:
            print(f"INITIAL_ADMIN_PASSWORD rejected: {exc.code} {exc.params}", file=sys.stderr)
            return 1
        user = users_repo.add(
            db,
            User(email=email, display_name="Administrator", role="admin", password_hash=hash_password(password)),
        )
        await db.flush()
        audit.record(
            db,
            actor=None,
            action="user.created",
            target_type="user",
            target_id=str(user.id),
            target_label=email,
            after=snapshot(user),
        )
        await db.commit()
    await get_engine().dispose()
    print(f"Admin {email} created.")
    return 0


def main() -> int:
    if get_settings().auth_mode != "local":
        print("AUTH_MODE is not 'local': admins come from the identity provider.", file=sys.stderr)
        return 1
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
    if not email or not password:
        print("Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD.", file=sys.stderr)
        return 2
    return asyncio.run(create(email, password))


if __name__ == "__main__":
    sys.exit(main())
