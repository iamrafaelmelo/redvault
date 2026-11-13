"""Authentication, sessions, CSRF and HTTP hardening."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import LOCAL_OPERATOR, SESSION_COOKIE, SESSION_TTL_HOURS, load_secret
from .models import AuthSession, User

_SECRET = load_secret()
_serializer = URLSafeTimedSerializer(_SECRET, salt="redvault-flash")


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def local_user(db: Session) -> User:
    """Return the single local operator, creating it when absent.

    REDVAULT is a private, loopback-only installation with one operator, so the
    identity is implicit: there is no password, no login form and no account
    creation step.
    """
    user = db.scalar(select(User).order_by(User.id))
    if user is not None:
        return user
    user = User(
        username=LOCAL_OPERATOR,
        password_hash="",
        display_name=LOCAL_OPERATOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def local_session(db: Session, request: Request) -> AuthSession:
    """Per-browser session that only carries the CSRF token.

    The cookie is never an authentication factor: every request is served as the
    local operator. It exists so mutating requests can present a token an
    attacker page cannot read.
    """
    user = local_user(db)
    now = datetime.now(timezone.utc)
    raw = request.cookies.get(SESSION_COOKIE)
    session = get_session(db, raw)
    if session and session.user_id == user.id:
        return session
    raw = secrets.token_urlsafe(48)
    session = AuthSession(
        token_hash=sha256(raw),
        user_id=user.id,
        csrf_token=new_csrf_token(),
        created_at=now,
        expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
        last_seen=now,
        ip=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:300],
    )
    db.add(session)
    user.last_login_at = now
    db.commit()
    request.state.pending_session_cookie = raw
    return session


def apply_session_cookie(response, request: Request) -> None:
    raw = getattr(request.state, "pending_session_cookie", None)
    if raw:
        response.set_cookie(
            SESSION_COOKIE,
            raw,
            max_age=SESSION_TTL_HOURS * 3600,
            httponly=True,
            samesite="lax",
            path="/",
        )
        request.state.pending_session_cookie = None


def get_session(db: Session, raw_token: str | None) -> AuthSession | None:
    if not raw_token:
        return None
    now = datetime.now(timezone.utc)
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == sha256(raw_token)))
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        db.delete(session)
        db.commit()
        return None
    if session.last_seen and (now - (session.last_seen if session.last_seen.tzinfo else session.last_seen.replace(tzinfo=timezone.utc))).total_seconds() > 300:
        session.last_seen = now
        db.commit()
    return session


def current_user(request: Request, db: Session) -> User | None:
    """The local operator is always signed in."""
    return local_user(db)


def get_user_or_401(request: Request, db: Session) -> User:
    return local_user(db)


def get_session_or_401(request: Request, db: Session) -> tuple[User, AuthSession]:
    return local_user(db), local_session(db, request)


def check_csrf(request: Request, form_token: str | None = None) -> None:
    """Validate a form token or the X-CSRF-Token header."""
    from .database import SessionLocal

    db = SessionLocal()
    try:
        session = local_session(db, request)
        supplied = form_token or request.headers.get("X-CSRF-Token")
        if not supplied or not hmac.compare_digest(supplied, session.csrf_token):
            raise HTTPException(status_code=403, detail="Falha na validação CSRF")
    finally:
        db.close()


def flash_cookie_name() -> str:
    return "rv_flash"


def encode_flash(payload: list[dict]) -> str:
    return _serializer.dumps(payload)


def decode_flash(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        value = _serializer.loads(raw, max_age=120)
        return value if isinstance(value, list) else []
    except (BadSignature, ValueError):
        return []


def set_flash(response, flashes: list[dict]) -> None:
    response.set_cookie(
        flash_cookie_name(),
        encode_flash(flashes),
        max_age=120,
        httponly=True,
        samesite="lax",
        path="/",
    )


def sanitize_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value
