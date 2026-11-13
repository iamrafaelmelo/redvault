"""Shared FastAPI dependencies and template rendering."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterator

import markdown as md
from fastapi import Depends, Request
from markupsafe import Markup
from sqlalchemy.orm import Session

from .config import CATEGORY_META, DIFFICULTIES, DIFFICULTY_LABELS, level_for_xp
from .database import SessionLocal
from .lab_manager import lab_manager
from .models import AuthSession, User
from .security import current_user, local_session
from .services.progress import xp_total


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    return current_user(request, db)


def get_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The only user this installation has; there is no authentication step."""
    return current_user(request, db)


def get_user_session(request: Request, db: Session = Depends(get_db)) -> tuple[User, AuthSession]:
    user = current_user(request, db)
    return user, local_session(db, request)


def render_markdown(value: str | None) -> Markup:
    if not value:
        return Markup("")
    html = md.markdown(
        value,
        extensions=["fenced_code", "tables", "sane_lists", "attr_list"],
    )
    return Markup(html)


def format_duration(seconds: int | None) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def time_ago(value: datetime | None) -> str:
    if not value:
        return "—"
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = (now - value).total_seconds()
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    if delta < 86400 * 30:
        return f"{int(delta // 86400)}d ago"
    return value.strftime("%d %b %Y")


def common_context(request: Request, db: Session, user: User | None, active: str) -> dict:
    session = None
    csrf = ""
    sidebar = {"xp": 0, "level": 1, "title": "Initiate", "percent": 0}
    if user:
        session = local_session(db, request)
        csrf = session.csrf_token
        xp = xp_total(db, user.id)
        level, title, floor, next_floor, _ = level_for_xp(xp)
        span = max(1, next_floor - floor) if next_floor > floor else 1
        sidebar = {
            "xp": xp,
            "level": level,
            "title": title,
            "percent": min(100, round((xp - floor) / span * 100)) if next_floor > floor else 100,
        }
    return {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "sidebar": sidebar,
        "active": active,
        "flashes": getattr(request.state, "flashes", []),
        "difficulties": DIFFICULTIES,
        "difficulty_labels": DIFFICULTY_LABELS,
        "category_meta": CATEGORY_META,
        "active_lab_count": len(lab_manager.active_labs()) if user else 0,
        "now": datetime.now(timezone.utc),
        "md": render_markdown,
        "duration": format_duration,
        "time_ago": time_ago,
    }
