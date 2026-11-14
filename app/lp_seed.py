"""Load curriculum JSON into the database, validating every reference.

Called at startup (idempotent). A curriculum referencing a non-existent lab,
KB document or Academy article aborts with a clear error instead of creating
empty cards in the UI.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .lp_models import (
    LearningActivity,
    LearningCapstone,
    LearningModule,
    LearningPath,
    LearningUnit,
)
from .lp_schema import CurriculumError, ValidationContext, collect_stats, validate_curriculum
from .models import Challenge

logger = logging.getLogger("redvault.lp")

CURRICULUM_DIR = Path(__file__).resolve().parent.parent / "content" / "learning_paths"


def build_context(db: Session) -> ValidationContext:
    """Snapshot of everything a curriculum may reference."""
    from .content import load_articles
    from .kb_models import KB_Document, KB_Source

    kb_slugs = set(db.scalars(select(KB_Document.slug)).all())
    academy_slugs = {a["slug"] for a in load_articles()}
    challenges = db.scalars(select(Challenge)).all()
    sources = set(db.scalars(select(KB_Source.name)).all())
    imported = db.scalar(
        select(KB_Document.id).where(KB_Document.origin == "imported").limit(1)
    ) is not None
    return ValidationContext(
        kb_slugs=kb_slugs,
        academy_slugs=academy_slugs,
        challenge_slugs={c.slug for c in challenges},
        challenge_kind={c.slug: c.kind for c in challenges},
        challenge_category={c.slug: (c.category.slug if c.category else "") for c in challenges},
        challenge_tags={c.slug: set(c.tags or []) for c in challenges},
        source_names=sources,
        kb_imported=imported,
    )


def load_curriculum_files(directory: Path | None = None) -> list[dict]:
    directory = directory or CURRICULUM_DIR
    if not directory.exists():
        return []
    docs = []
    for path in sorted(directory.glob("*.json")):
        try:
            docs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise CurriculumError(f"{path.name}: JSON inválido ({exc})") from exc
    return docs


def validate_all(db: Session, docs: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    """Validate every curriculum. Returns (docs, warnings) or raises."""
    docs = docs if docs is not None else load_curriculum_files()
    ctx = build_context(db)
    warnings: list[str] = []
    for doc in docs:
        ctx.path_slugs = {d.get("slug", "") for d in docs}
        warnings.extend(validate_curriculum(doc, ctx))
    return docs, warnings


def _upsert_activity(db: Session, unit: LearningUnit, data: dict, position: int) -> None:
    act = db.scalar(
        select(LearningActivity).where(
            LearningActivity.unit_id == unit.id, LearningActivity.slug == data["slug"]
        )
    )
    if not act:
        act = LearningActivity(unit_id=unit.id, slug=data["slug"])
        db.add(act)
    act.kind = data["kind"]
    act.title = data["title"]
    act.position = position
    act.body_md = data.get("body_md", "")
    act.required = data.get("required", True)
    act.estimated_minutes = data.get("estimated_minutes", 15)
    act.kb_slug = data.get("kb_slug", "")
    act.academy_slug = data.get("academy_slug", "")
    act.challenge_slug = data.get("challenge_slug", "")
    act.gap = data.get("gap", "")
    act.equipment = data.get("equipment", "")
    key = {"questions": data.get("questions", []), "quiz": data.get("quiz", False)}
    if data.get("answer_key"):
        key["answer_key"] = data["answer_key"]
    act.answer_key = key


def _upsert_unit(db: Session, module: LearningModule, data: dict, position: int) -> LearningUnit:
    unit = db.scalar(
        select(LearningUnit).where(LearningUnit.module_id == module.id, LearningUnit.slug == data["slug"])
    )
    if not unit:
        unit = LearningUnit(module_id=module.id, slug=data["slug"])
        db.add(unit)
    unit.title = data["title"]
    unit.position = position
    unit.objective = data.get("objective", "")
    unit.competencies = data.get("competencies", [])
    unit.estimated_minutes = data.get("estimated_minutes", 60)
    db.flush()
    for i, act in enumerate(data["activities"], 1):
        _upsert_activity(db, unit, act, i)
    return unit


def _upsert_module(db: Session, path: LearningPath, data: dict, position: int) -> LearningModule:
    module = db.scalar(
        select(LearningModule).where(LearningModule.path_id == path.id, LearningModule.slug == data["slug"])
    )
    if not module:
        module = LearningModule(path_id=path.id, slug=data["slug"])
        db.add(module)
    module.title = data["title"]
    module.position = position
    module.summary = data.get("summary", "")
    module.objective = data["objective"]
    module.competencies = data.get("competencies", [])
    module.prerequisites = data.get("prerequisites", "")
    module.completion = data.get("completion", "")
    module.estimated_minutes = data.get("estimated_minutes", 180)
    module.requires_module = data.get("requires_module", "")
    module.gap = data.get("gap", "")
    db.flush()
    for i, unit in enumerate(data["units"], 1):
        _upsert_unit(db, module, unit, i)
    return module


def seed_path(db: Session, data: dict) -> LearningPath:
    path = db.scalar(select(LearningPath).where(LearningPath.slug == data["slug"]))
    if not path:
        path = LearningPath(slug=data["slug"])
        db.add(path)
    path.title = data["title"]
    path.codename = data.get("codename", "")
    path.domain = data.get("domain", "")
    path.summary = data["summary"]
    path.description = data.get("description", "")
    path.entry_level = data["entry_level"]
    path.exit_level = data["exit_level"]
    path.estimated_hours = data["estimated_hours"]
    path.priority = data.get("priority", 100)
    path.phase = data.get("phase", 1)
    path.icon = data.get("icon", "route")
    path.accent = data.get("accent", "red")
    path.prerequisites = data.get("prerequisites", [])
    path.competencies = data.get("competencies", [])
    path.tools = data.get("tools", [])
    path.equipment = data.get("equipment", "")
    path.status = data.get("status", "published")
    db.flush()

    # Modules removed from the JSON are removed from the DB (curriculum is source of truth)
    keep = {m["slug"] for m in data["modules"]}
    stale = db.scalars(select(LearningModule).where(LearningModule.path_id == path.id)).all()
    for module in stale:
        if module.slug not in keep:
            db.delete(module)
    db.flush()

    for i, mod in enumerate(data["modules"], 1):
        _upsert_module(db, path, mod, i)

    cap = db.scalar(select(LearningCapstone).where(LearningCapstone.path_id == path.id))
    cdata = data["capstone"]
    if not cap:
        cap = LearningCapstone(path_id=path.id)
        db.add(cap)
    cap.objective = cdata["objective"]
    cap.scope_md = cdata.get("scope_md", "")
    cap.resources_md = cdata.get("resources_md", "")
    cap.steps_md = cdata.get("steps_md", "")
    cap.success_criteria = cdata["success_criteria"]
    cap.evidence = cdata["evidence"]
    cap.expected_result = cdata.get("expected_result", "")
    cap.grading_md = cdata["grading_md"]
    cap.challenge_slug = cdata.get("challenge_slug", "")
    return path


def seed_all(db: Session) -> dict:
    """Validate and upsert every curriculum. Raises CurriculumError if broken."""
    docs, warnings = validate_all(db)
    if not docs:
        return {"paths": 0, "modules": 0, "activities": 0, "warnings": [], "stats": {}}
    stats = {}
    for doc in docs:
        seed_path(db, doc)
        stats[doc["slug"]] = collect_stats(doc)
    db.commit()
    return {
        "paths": len(docs),
        "modules": sum(s["modules"] for s in stats.values()),
        "activities": sum(s["activities"] for s in stats.values()),
        "warnings": warnings,
        "stats": stats,
    }


def duplicate_path(db: Session, source_slug: str, new_slug: str, new_title: str) -> LearningPath:
    """Clone a path (and its whole tree) into a custom, editable copy."""
    src = db.scalar(select(LearningPath).where(LearningPath.slug == source_slug))
    if not src:
        raise ValueError("trilha de origem não encontrada")
    if db.scalar(select(LearningPath).where(LearningPath.slug == new_slug)):
        raise ValueError("já existe uma trilha com esse slug")

    copy = LearningPath(
        slug=new_slug,
        title=new_title,
        codename="CUSTOM",
        domain=src.domain,
        summary=src.summary,
        description=src.description,
        entry_level=src.entry_level,
        exit_level=src.exit_level,
        estimated_hours=src.estimated_hours,
        priority=src.priority,
        phase=src.phase,
        icon=src.icon,
        accent=src.accent,
        prerequisites=list(src.prerequisites or []),
        competencies=list(src.competencies or []),
        tools=list(src.tools or []),
        equipment=src.equipment,
        is_custom=True,
    )
    db.add(copy)
    db.flush()
    for module in src.modules:
        mcopy = LearningModule(
            path_id=copy.id, slug=module.slug, title=module.title, position=module.position,
            summary=module.summary, objective=module.objective, competencies=list(module.competencies or []),
            prerequisites=module.prerequisites, completion=module.completion,
            estimated_minutes=module.estimated_minutes, requires_module=module.requires_module,
            gap=module.gap,
        )
        db.add(mcopy)
        db.flush()
        for unit in module.units:
            ucopy = LearningUnit(
                module_id=mcopy.id, slug=unit.slug, title=unit.title, position=unit.position,
                objective=unit.objective, competencies=list(unit.competencies or []),
                estimated_minutes=unit.estimated_minutes,
            )
            db.add(ucopy)
            db.flush()
            for act in unit.activities:
                db.add(LearningActivity(
                    unit_id=ucopy.id, slug=act.slug, kind=act.kind, title=act.title,
                    position=act.position, body_md=act.body_md, required=act.required,
                    estimated_minutes=act.estimated_minutes, kb_slug=act.kb_slug,
                    academy_slug=act.academy_slug, challenge_slug=act.challenge_slug,
                    answer_key=act.answer_key or {}, gap=act.gap,
                    equipment=act.equipment,
                ))
    if src.capstone:
        c = src.capstone
        db.add(LearningCapstone(
            path_id=copy.id, objective=c.objective, scope_md=c.scope_md,
            resources_md=c.resources_md, steps_md=c.steps_md,
            success_criteria=list(c.success_criteria or []), evidence=list(c.evidence or []),
            expected_result=c.expected_result, grading_md=c.grading_md,
            challenge_slug=c.challenge_slug,
        ))
    db.commit()
    return copy