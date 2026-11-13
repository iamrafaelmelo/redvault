"""Relational model for the platform.

Content (challenges, hints, references, paths) is seeded from lab manifests,
while user state (progress, submissions, sessions, labs) lives only here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Kept for schema compatibility with existing databases. REDVAULT has no
    # login, so this column is always empty.
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(80), default="Operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    progress: Mapped[list["Progress"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship(back_populates="sessions")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(40), default="terminal")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    challenges: Mapped[list["Challenge"]] = relationship(back_populates="category")


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="challenge", index=True)  # challenge|machine|realistic
    title: Mapped[str] = mapped_column(String(160))
    codename: Mapped[str] = mapped_column(String(80), default="")
    summary: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="easy", index=True)
    xp: Mapped[int] = mapped_column(Integer, default=100)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=20)
    lab_dir: Mapped[str] = mapped_column(String(120))
    story_md: Mapped[str] = mapped_column(Text, default="")
    objective_md: Mapped[str] = mapped_column(Text, default="")
    rules_md: Mapped[str] = mapped_column(Text, default="")
    tech: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category: Mapped[Category | None] = relationship(back_populates="challenges")
    flags: Mapped[list["Flag"]] = relationship(back_populates="challenge", cascade="all, delete-orphan", order_by="Flag.sort_order")
    hints: Mapped[list["Hint"]] = relationship(back_populates="challenge", cascade="all, delete-orphan", order_by="Hint.level")
    solution: Mapped["Solution | None"] = relationship(back_populates="challenge", cascade="all, delete-orphan", uselist=False)
    references: Mapped[list["Reference"]] = relationship(back_populates="challenge", cascade="all, delete-orphan")
    lab_sessions: Mapped[list["LabSession"]] = relationship(back_populates="challenge", cascade="all, delete-orphan")


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (UniqueConstraint("challenge_id", "key", name="uq_flag_challenge_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(100))
    flag_type: Mapped[str] = mapped_column(String(20), default="user")  # user|root|api|hidden|bonus
    points: Mapped[int] = mapped_column(Integer, default=25)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_objective: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    challenge: Mapped[Challenge] = relationship(back_populates="flags")


class Hint(Base):
    __tablename__ = "hints"
    __table_args__ = (UniqueConstraint("challenge_id", "level", name="uq_hint_challenge_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    level: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120))
    body_md: Mapped[str] = mapped_column(Text)
    cost: Mapped[int] = mapped_column(Integer, default=10)

    challenge: Mapped[Challenge] = relationship(back_populates="hints")


class Solution(Base):
    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), unique=True)
    walkthrough_md: Mapped[str] = mapped_column(Text, default="")
    root_cause_md: Mapped[str] = mapped_column(Text, default="")
    mitigation_md: Mapped[str] = mapped_column(Text, default="")

    challenge: Mapped[Challenge] = relationship(back_populates="solution")


class Reference(Base):
    __tablename__ = "references"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(30), default="official")
    description: Mapped[str] = mapped_column(String(300), default="")

    challenge: Mapped[Challenge] = relationship(back_populates="references")


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", name="uq_progress_user_challenge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    hint_penalty: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    solution_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_without_hints: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[User] = relationship(back_populates="progress")
    challenge: Mapped[Challenge] = relationship()


class FlagSubmission(Base):
    __tablename__ = "flag_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    flag_id: Mapped[int | None] = mapped_column(ForeignKey("flags.id", ondelete="SET NULL"))
    flag_key: Mapped[str] = mapped_column(String(40), default="")
    value_hash: Mapped[str] = mapped_column(String(64))
    value_masked: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="incorrect")
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class HintUnlock(Base):
    __tablename__ = "hint_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "hint_id", name="uq_hint_unlock"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    hint_id: Mapped[int] = mapped_column(ForeignKey("hints.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ObjectiveState(Base):
    __tablename__ = "objective_states"
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", "flag_key", name="uq_objective_state"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    flag_key: Mapped[str] = mapped_column(String(40))
    met: Mapped[bool] = mapped_column(Boolean, default=False)
    met_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[str] = mapped_column(String(300), default="")


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    message: Mapped[str] = mapped_column(String(300))
    challenge_id: Mapped[int | None] = mapped_column(ForeignKey("challenges.id", ondelete="SET NULL"))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(300))
    icon: Mapped[str] = mapped_column(String(40), default="trophy")
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    achievement: Mapped[Achievement] = relationship()


class LabSession(Base):
    __tablename__ = "lab_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    port: Mapped[int] = mapped_column(Integer)
    pid: Mapped[int | None] = mapped_column(Integer)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    state_dir: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="starting", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reset_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(String(500), default="")

    challenge: Mapped[Challenge] = relationship(back_populates="lab_sessions")


class Path(Base):
    __tablename__ = "paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    estimated_hours: Mapped[int] = mapped_column(Integer, default=8)
    icon: Mapped[str] = mapped_column(String(40), default="route")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    items: Mapped[list["PathChallenge"]] = relationship(back_populates="path", cascade="all, delete-orphan", order_by="PathChallenge.position")


class PathChallenge(Base):
    __tablename__ = "path_challenges"
    __table_args__ = (UniqueConstraint("path_id", "challenge_id", name="uq_path_challenge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("paths.id", ondelete="CASCADE"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)

    path: Mapped[Path] = relationship(back_populates="items")
    challenge: Mapped[Challenge] = relationship()


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_setting"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(Text, default="")
