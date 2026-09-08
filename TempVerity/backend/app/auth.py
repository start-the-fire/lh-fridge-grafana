from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.config import get_settings
from .models import Session as LoginSession, Setting, User

COOKIE_NAME = "tempverity_session"
password_hasher = PasswordHasher()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def auth_enabled(db: Session) -> bool:
    setting = db.get(Setting, "auth")
    if setting is None:
        return False
    return bool(json.loads(setting.value_json).get("enabled", False))


def session_lifetime_minutes(db: Session) -> int:
    setting = db.get(Setting, "auth")
    values = json.loads(setting.value_json) if setting else {}
    return max(5, int(values.get("sessionMinutes", get_settings().session_lifetime_days * 24 * 60)))


def ensure_admin(db: Session) -> None:
    admin = db.scalar(select(User).where(User.username == "administrator"))
    if admin is None:
        password = get_settings().admin_password
        db.add(User(username="administrator", password_hash=password_hasher.hash(password), role="admin", enabled=True))
        db.commit()
    elif not admin.role:
        admin.role = "admin"
        db.commit()


def login(db: Session, username: str | None, password: str) -> str:
    if username:
        candidates = list(db.scalars(select(User).where(User.username == username, User.enabled.is_(True))).all())
    else:
        candidates = list(
            db.scalars(
                select(User)
                .where(User.enabled.is_(True), User.role.in_(["admin", "viewer"]))
                .order_by(User.role.asc(), User.id.asc())
            ).all()
        )

    user = None
    for candidate in candidates:
        try:
            if password_hasher.verify(candidate.password_hash, password):
                user = candidate
                break
        except Exception:
            continue
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    user.last_login = now
    db.add(LoginSession(user_id=user.id, token_hash=_hash_token(token), expires_at=now + timedelta(minutes=session_lifetime_minutes(db))))
    db.commit()
    return token


def configure_auth(
    db: Session,
    *,
    enabled: bool,
    dashboard_requires_auth: bool,
    session_minutes: int,
    admin_password: str | None = None,
    viewer_password: str | None = None,
) -> None:
    admin = db.scalar(select(User).where(User.username == "administrator"))
    if admin is None:
        admin = User(username="administrator", password_hash=password_hasher.hash(get_settings().admin_password), role="admin", enabled=True)
        db.add(admin)
    if admin_password and admin_password.strip():
        admin.password_hash = password_hasher.hash(admin_password)
    viewer = db.scalar(select(User).where(User.username == "viewer"))
    if viewer_password and viewer_password.strip():
        if viewer is None:
            viewer = User(username="viewer", password_hash=password_hasher.hash(viewer_password), role="viewer", enabled=True)
            db.add(viewer)
        else:
            viewer.password_hash = password_hasher.hash(viewer_password)
            viewer.enabled = True
    auth_setting = db.get(Setting, "auth")
    values = json.loads(auth_setting.value_json) if auth_setting else {}
    values.update({"enabled": enabled, "dashboardRequiresAuth": dashboard_requires_auth, "sessionMinutes": session_minutes, "adminUsername": "administrator", "viewerConfigured": viewer is not None and viewer.enabled})
    if auth_setting is None:
        db.add(Setting(key="auth", value_json=json.dumps(values)))
    else:
        auth_setting.value_json = json.dumps(values)
    db.commit()


def reset_password(db: Session, username: str, password: str) -> None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise ValueError(f"User not found: {username}")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    user.password_hash = password_hasher.hash(password)
    user.enabled = True
    db.query(LoginSession).filter(LoginSession.user_id == user.id).delete()
    db.commit()


def current_user(request: Request, db: Session, required: bool = True) -> User | None:
    if not auth_enabled(db):
        return None
    token = request.cookies.get(COOKIE_NAME)
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == _hash_token(token or "")))
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at if session is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if session is None or expires_at < now:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None
    session.last_seen_at = now
    db.commit()
    user = db.get(User, session.user_id)
    if user is None or not user.enabled:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
