"""Local login, refresh rotation, logout, password change and own-account preferences."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import CurrentUser
from app.auth.provider import to_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_fits_bcrypt,
    verify_password,
)
from app.models import User
from app.repositories import audit as audit_repo
from app.repositories import refresh_tokens as tokens_repo
from app.repositories import users as users_repo
from app.schemas.auth import MeUpdate
from app.services import audit
from app.services.settings import SettingKey, get_values

LOGIN_FAILED = "auth.login_failed"
LOGIN_OK = "auth.login"


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    max_age_seconds: int
    user: User


async def _issue(db: AsyncSession, user: User) -> IssuedSession:
    hours = int((await get_values(db, SettingKey.SESSION_HOURS))[SettingKey.SESSION_HOURS])
    raw, token_hash = generate_refresh_token()
    tokens_repo.add(db, user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(hours=hours))
    return IssuedSession(create_access_token(user.id), raw, hours * 3600, user)


async def _check_rate_limit(db: AsyncSession, email: str) -> None:
    limit = (await get_values(db, SettingKey.LOGIN_RATE_LIMIT))[SettingKey.LOGIN_RATE_LIMIT]
    window = timedelta(minutes=int(limit["window_minutes"]))
    now = datetime.now(UTC)
    since = now - window
    last_ok = await audit_repo.latest(db, action=LOGIN_OK, target_label=email)
    if last_ok is not None and last_ok > since:
        since = last_ok
    failures = await audit_repo.count_since(db, action=LOGIN_FAILED, target_label=email, since=since)
    if failures >= int(limit["max_attempts"]):
        raise AppError(
            429,
            "auth.too_many_attempts",
            {"minutes": int(limit["window_minutes"]), "retry_after_seconds": int(window.total_seconds())},
        )


async def login(db: AsyncSession, email: str, password: str, request: Request | None) -> IssuedSession:
    email = email.lower()
    await _check_rate_limit(db, email)
    user = await users_repo.get_by_email(db, email)
    valid = user is not None and user.deleted_at is None and verify_password(password, user.password_hash)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # same timing as a known email
    if not valid or user is None:
        audit.record(db, actor=None, action=LOGIN_FAILED, target_type="user", target_label=email, request=request)
        await db.commit()
        # Same answer for unknown email, wrong password and deactivated account.
        raise AppError(401, "auth.invalid_credentials")
    user.last_login_at = datetime.now(UTC)
    session = await _issue(db, user)
    audit.record(
        db,
        actor=to_current_user(user),
        action=LOGIN_OK,
        target_type="user",
        target_id=str(user.id),
        target_label=email,
        request=request,
    )
    await db.commit()
    return session


def _within_grace(rotated_at: datetime | None) -> bool:
    grace = get_settings().refresh_token_reuse_grace_seconds
    return rotated_at is not None and (datetime.now(UTC) - rotated_at).total_seconds() <= grace


async def refresh(db: AsyncSession, raw_token: str | None, request: Request | None) -> IssuedSession:
    invalid = AppError(401, "auth.session_expired")
    if not raw_token:
        raise invalid
    stored = await tokens_repo.get_by_hash(db, hash_refresh_token(raw_token))
    now = datetime.now(UTC)
    if stored is None or stored.expires_at < now:
        raise invalid
    if stored.revoked_at is not None:
        if stored.rotated_at is not None and not _within_grace(stored.rotated_at):
            # A rotated token used again after the grace window: likely stolen. End every session.
            await tokens_repo.revoke_all(db, stored.user_id, at=now)
            audit.record(
                db,
                actor=None,
                action="auth.refresh_reuse_detected",
                target_type="user",
                target_id=str(stored.user_id),
                request=request,
            )
            await db.commit()
            raise invalid
        if stored.rotated_at is None:
            raise invalid  # revoked by logout / password change / deactivation
    user = await users_repo.get_active_by_id(db, stored.user_id)
    if user is None:
        raise invalid
    if stored.revoked_at is None:
        stored.revoked_at = now
        stored.rotated_at = now
    # else: rotated a moment ago and the new cookie never reached this tab — issue a fresh pair.
    session = await _issue(db, user)
    await db.commit()
    return session


async def logout(db: AsyncSession, raw_token: str | None, request: Request | None) -> None:
    if not raw_token:
        return
    stored = await tokens_repo.get_by_hash(db, hash_refresh_token(raw_token))
    if stored is None or stored.revoked_at is not None:
        return
    stored.revoked_at = datetime.now(UTC)
    user = await users_repo.get_by_id(db, stored.user_id)
    audit.record(
        db,
        actor=to_current_user(user) if user else None,
        action="auth.logout",
        target_type="user",
        target_id=str(stored.user_id),
        target_label=user.email if user else None,
        request=request,
    )
    await db.commit()


async def validate_new_password(db: AsyncSession, password: str) -> None:
    minimum = int((await get_values(db, SettingKey.PASSWORD_MIN_LENGTH))[SettingKey.PASSWORD_MIN_LENGTH])
    if len(password) < minimum:
        raise AppError(422, "auth.password_too_short", {"min": minimum})
    if not password_fits_bcrypt(password):
        raise AppError(422, "auth.password_too_long", {"max_bytes": BCRYPT_MAX_PASSWORD_BYTES})


async def change_password(
    db: AsyncSession,
    actor: CurrentUser,
    current_password: str,
    new_password: str,
    raw_refresh: str | None,
    request: Request | None,
) -> None:
    user = await users_repo.get_active_by_id(db, actor.id)
    if user is None:
        raise AppError(401, "auth.not_authenticated")
    if not verify_password(current_password, user.password_hash):
        raise AppError(403, "auth.current_password_incorrect")
    if new_password == current_password:
        raise AppError(422, "auth.password_unchanged")
    await validate_new_password(db, new_password)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await tokens_repo.revoke_all(
        db, user.id, at=datetime.now(UTC), keep_hash=hash_refresh_token(raw_refresh) if raw_refresh else None
    )
    audit.record(
        db,
        actor=actor,
        action="auth.password_changed",
        target_type="user",
        target_id=str(user.id),
        target_label=user.email,
        request=request,
    )
    await db.commit()


def _prefs(user: User) -> dict[str, Any]:
    return {"display_name": user.display_name, "preferred_language": user.preferred_language, "theme": user.theme}


async def get_me(db: AsyncSession, actor: CurrentUser) -> User:
    user = await users_repo.get_active_by_id(db, actor.id)
    if user is None:
        raise AppError(401, "auth.not_authenticated")
    return user


async def update_me(db: AsyncSession, actor: CurrentUser, body: MeUpdate, request: Request | None) -> User:
    user = await get_me(db, actor)
    before = _prefs(user)
    for field, value in body.model_dump(exclude_unset=True).items():
        # preferred_language may be cleared (null = follow the default language setting).
        if value is None and field != "preferred_language":
            raise AppError(422, "validation.failed", {"fields": [{"field": field, "type": "null"}]})
        setattr(user, field, value)
    if _prefs(user) != before:
        audit.record(
            db,
            actor=actor,
            action="account.updated",
            target_type="user",
            target_id=str(user.id),
            target_label=user.email,
            before=before,
            after=_prefs(user),
            request=request,
        )
    await db.commit()
    await db.refresh(user)
    return user
