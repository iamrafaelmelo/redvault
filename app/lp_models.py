"""Learning Paths Engine — data model.

Deliberately separate from the legacy ``paths`` / ``path_challenges`` tables,
which only carry flat sequences of challenge slugs. A learning path here is a
full curriculum:

    LearningPath -> LearningModule -> LearningUnit -> LearningActivity

* **Path** is the programme (Web Application Pentesting, AD, Hardware...).
* **Module** is a stage with an entry/exit level and its own prerequisites.
* **Unit** is the discipline inside the module (a coherent block of theory).
* **Activity** is the atomic, trackable item: theory reading, exercise, lab,
  challenge, assessment question set or project milestone.

Every activity that points at platform content stores the *slug*, never a
foreign key, so a lab or document that is deleted from the platform shows up
as a broken link during seed validation instead of silently disappearing.
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


# Activity kinds understood by the UI and the progress engine.
ACTIVITY_KINDS = (
    "theory",       # read a KB / Academy document
    "exercises",    # guided practical tasks written for this module
    "lab",          # a platform lab or machine (slug -> challenges)
    "assessment",   # graded questions / request analysis
    "project",      # capstone milestone
    "external",     # verified external reference, marked manually
)

ACTIVITY_STATES = ("not_started", "in_progress", "completed", "review")


class LearningPath(Base):
    __tablename__ = "lp_paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    codename: Mapped[str] = mapped_column(String(40), default="")
    domain: Mapped[str] = mapped_column(String(60), default="")  # web, infra, hardware...
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    entry_level: Mapped[str] = mapped_column(String(40), default="iniciante")
    exit_level: Mapped[str] = mapped_column(String(40), default="avancado")
    estimated_hours: Mapped[int] = mapped_column(Integer, default=40)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    phase: Mapped[int] = mapped_column(Integer, default=1)
    icon: Mapped[str] = mapped_column(String(40), default="route")
    accent: Mapped[str] = mapped_column(String(40), default="red")
    # list of path slugs
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    # list of skill strings shown on the card
    competencies: Mapped[list] = mapped_column(JSON, default=list)
    # list of tool slugs/names the path requires
    tools: Mapped[list] = mapped_column(JSON, default=list)
    equipment: Mapped[str] = mapped_column(Text, default="")  # "software only" vs physical
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    modules: Mapped[list["LearningModule"]] = relationship(
        back_populates="path", cascade="all, delete-orphan", order_by="LearningModule.position"
    )
    capstone: Mapped["LearningCapstone | None"] = relationship(
        back_populates="path", cascade="all, delete-orphan", uselist=False
    )


class LearningModule(Base):
    __tablename__ = "lp_modules"
    __table_args__ = (UniqueConstraint("path_id", "slug", name="uq_lp_module_path_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("lp_paths.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")       # learning objective
    competencies: Mapped[list] = mapped_column(JSON, default=list)
    prerequisites: Mapped[str] = mapped_column(Text, default="")   # free text
    completion: Mapped[str] = mapped_column(Text, default="")      # completion criteria
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=180)
    # slug of module in same path that must be completed first (soft gate)
    requires_module: Mapped[str] = mapped_column(String(100), default="")
    # explicit curriculum gap flag + what must be written
    gap: Mapped[str] = mapped_column(Text, default="")

    path: Mapped[LearningPath] = relationship(back_populates="modules")
    units: Mapped[list["LearningUnit"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="LearningUnit.position"
    )


class LearningUnit(Base):
    __tablename__ = "lp_units"
    __table_args__ = (UniqueConstraint("module_id", "slug", name="uq_lp_unit_module_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("lp_modules.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    objective: Mapped[str] = mapped_column(Text, default="")
    competencies: Mapped[list] = mapped_column(JSON, default=list)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)

    module: Mapped[LearningModule] = relationship(back_populates="units")
    activities: Mapped[list["LearningActivity"]] = relationship(
        back_populates="unit", cascade="all, delete-orphan", order_by="LearningActivity.position"
    )


class LearningActivity(Base):
    __tablename__ = "lp_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("lp_units.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="theory")
    title: Mapped[str] = mapped_column(String(250))
    position: Mapped[int] = mapped_column(Integer, default=0)
    body_md: Mapped[str] = mapped_column(Text, default="")      # exercises / assessment text
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    # --- targets (exactly one normally set) ---
    kb_slug: Mapped[str] = mapped_column(String(120), default="")        # kb_documents.slug
    academy_slug: Mapped[str] = mapped_column(String(80), default="")    # content/academy slug
    challenge_slug: Mapped[str] = mapped_column(String(80), default="")  # labs
    # --- answer key for assessments (server side only) ---
    answer_key: Mapped[dict] = mapped_column(JSON, default=dict)
    gap: Mapped[str] = mapped_column(Text, default="")
    # What the activity physically needs. Most paths are "somente software";
    # hardware paths must say plainly when a task cannot be done without a
    # device, so nobody assumes the operator owns a scope or a probe.
    equipment: Mapped[str] = mapped_column(String(40), default="")

    unit: Mapped[LearningUnit] = relationship(back_populates="activities")

    @property
    def target_url(self) -> str:
        if self.kb_slug:
            return f"/kb/d/{self.kb_slug}"
        if self.academy_slug:
            return f"/academy/{self.academy_slug}"
        if self.challenge_slug:
            return f"/lab/{self.challenge_slug}"
        return ""


class LearningCapstone(Base):
    __tablename__ = "lp_capstones"

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("lp_paths.id", ondelete="CASCADE"), unique=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    scope_md: Mapped[str] = mapped_column(Text, default="")
    resources_md: Mapped[str] = mapped_column(Text, default="")
    steps_md: Mapped[str] = mapped_column(Text, default="")
    success_criteria: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    expected_result: Mapped[str] = mapped_column(Text, default="")
    grading_md: Mapped[str] = mapped_column(Text, default="")
    challenge_slug: Mapped[str] = mapped_column(String(80), default="")

    path: Mapped[LearningPath] = relationship(back_populates="capstone")


class LearningActivityProgress(Base):
    """Per-activity state for the single local operator."""

    __tablename__ = "lp_progress"
    __table_args__ = (UniqueConstraint("user_id", "activity_id", name="uq_lp_progress_user_activity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("lp_activities.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(20), default="not_started")
    notes: Mapped[str] = mapped_column(Text, default="")        # anotações pessoais
    difficulties: Mapped[str] = mapped_column(Text, default="")  # dificuldades
    result: Mapped[str] = mapped_column(Text, default="")        # resultados
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    revisit: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int | None] = mapped_column(Integer)           # assessment score %
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LearningAssessmentAttempt(Base):
    __tablename__ = "lp_assessment_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("lp_activities.id", ondelete="CASCADE"), index=True)
    submitted: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class LearningCertificate(Base):
    __tablename__ = "lp_certificates"
    __table_args__ = (UniqueConstraint("user_id", "path_id", name="uq_lp_certificate_user_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("lp_paths.id", ondelete="CASCADE"), index=True)
    serial: Mapped[str] = mapped_column(String(40), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    activities_completed: Mapped[int] = mapped_column(Integer, default=0)
    hours_logged: Mapped[int] = mapped_column(Integer, default=0)