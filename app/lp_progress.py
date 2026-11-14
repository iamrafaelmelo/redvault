"""Progress engine, recommendations and certificates for Learning Paths."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .lp_models import (
    LearningActivity,
    LearningActivityProgress,
    LearningCertificate,
    LearningModule,
    LearningPath,
    LearningUnit,
)
from .models import Progress as LabProgress


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def load_path(db: Session, slug: str) -> LearningPath | None:
    return db.scalar(
        select(LearningPath)
        .options(
            selectinload(LearningPath.capstone),
            selectinload(LearningPath.modules)
            .selectinload(LearningModule.units)
            .selectinload(LearningUnit.activities),
        )
        .where(LearningPath.slug == slug)
    )


def load_paths(db: Session) -> list[LearningPath]:
    return list(db.scalars(
        select(LearningPath)
        .options(
            selectinload(LearningPath.capstone),
            selectinload(LearningPath.modules)
            .selectinload(LearningModule.units)
            .selectinload(LearningUnit.activities),
        )
        .order_by(LearningPath.phase, LearningPath.priority, LearningPath.title)
    ).unique().all())


def activity_ids(path: LearningPath) -> list[int]:
    return [a.id for m in path.modules for u in m.units for a in u.activities]


def progress_map(db: Session, user_id: int, path: LearningPath) -> dict[int, LearningActivityProgress]:
    ids = activity_ids(path)
    if not ids:
        return {}
    rows = db.scalars(
        select(LearningActivityProgress).where(
            LearningActivityProgress.user_id == user_id,
            LearningActivityProgress.activity_id.in_(ids),
        )
    ).all()
    return {r.activity_id: r for r in rows}


# ---------------------------------------------------------------------------
# Path / module progress
# ---------------------------------------------------------------------------

@dataclass
class PathProgress:
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    review: int = 0
    percent: int = 0
    required_total: int = 0
    required_done: int = 0
    minutes_done: int = 0
    minutes_total: int = 0
    by_kind: dict = field(default_factory=dict)
    module_state: dict = field(default_factory=dict)     # module slug -> dict
    completed_all: bool = False

    @property
    def started(self) -> bool:
        return self.completed > 0 or self.in_progress > 0


def compute_path_progress(path: LearningPath, pmap: dict[int, LearningActivityProgress]) -> PathProgress:
    pp = PathProgress()
    for module in path.modules:
        mod_total = mod_done = mod_review = 0
        mod_required = mod_required_done = 0
        mod_minutes = mod_minutes_done = 0
        for unit in module.units:
            for act in unit.activities:
                state = pmap[act.id].state if act.id in pmap else "not_started"
                pp.total += 1
                mod_total += 1
                pp.minutes_total += act.estimated_minutes
                mod_minutes += act.estimated_minutes
                if act.required:
                    pp.required_total += 1
                    mod_required += 1
                pp.by_kind.setdefault(act.kind, {"total": 0, "done": 0})
                pp.by_kind[act.kind]["total"] += 1
                if state == "completed":
                    pp.completed += 1
                    mod_done += 1
                    pp.minutes_done += act.estimated_minutes
                    mod_minutes_done += act.estimated_minutes
                    pp.by_kind[act.kind]["done"] += 1
                    if act.required:
                        pp.required_done += 1
                        mod_required_done += 1
                elif state == "in_progress":
                    pp.in_progress += 1
                elif state == "review":
                    pp.review += 1
                    mod_review += 1
        pp.module_state[module.slug] = {
            "total": mod_total,
            "completed": mod_done,
            "review": mod_review,
            "required": mod_required,
            "required_done": mod_required_done,
            "minutes": mod_minutes,
            "minutes_done": mod_minutes_done,
            "percent": round(mod_done / mod_total * 100) if mod_total else 0,
            "complete": mod_total > 0 and mod_done == mod_total,
        }
    pp.percent = round(pp.completed / pp.total * 100) if pp.total else 0
    # A path is complete only when every required activity is done AND the
    # capstone project activity is done. Opening pages is not enough.
    pp.completed_all = pp.required_total > 0 and pp.required_done == pp.required_total
    return pp


def module_gate_met(path: LearningPath, module: LearningModule, pp: PathProgress) -> bool:
    """Soft gate: the module's declared predecessor must be complete."""
    if not module.requires_module:
        return True
    state = pp.module_state.get(module.requires_module)
    return bool(state and state["complete"])


# ---------------------------------------------------------------------------
# Activity state mutations
# ---------------------------------------------------------------------------

VALID_STATES = {"not_started", "in_progress", "completed", "review"}


def get_or_create(db: Session, user_id: int, activity_id: int) -> LearningActivityProgress:
    row = db.scalar(
        select(LearningActivityProgress).where(
            LearningActivityProgress.user_id == user_id,
            LearningActivityProgress.activity_id == activity_id,
        )
    )
    if not row:
        row = LearningActivityProgress(user_id=user_id, activity_id=activity_id, state="not_started")
        db.add(row)
        db.flush()
    return row


def set_state(db: Session, user_id: int, activity_id: int, state: str) -> LearningActivityProgress:
    if state not in VALID_STATES:
        raise ValueError(f"estado inválido: {state}")
    row = get_or_create(db, user_id, activity_id)
    now = utcnow()
    if state == "completed" and row.state != "completed":
        row.completed_at = now
    if state == "not_started":
        row.completed_at = None
    if state in {"in_progress", "completed"} and not row.started_at:
        row.started_at = now
    row.state = state
    row.updated_at = now
    db.commit()
    return row


def update_fields(db: Session, user_id: int, activity_id: int, **fields) -> LearningActivityProgress:
    row = get_or_create(db, user_id, activity_id)
    for key in ("notes", "difficulties", "result", "favorite", "revisit", "score"):
        if key in fields and fields[key] is not None:
            setattr(row, key, fields[key])
    row.updated_at = utcnow()
    db.commit()
    return row


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    kind: str          # next_activity | review | gap | prerequisite | lab
    title: str
    reason: str
    path_slug: str
    url: str
    priority: int


def recommend(db: Session, user_id: int, limit: int = 12) -> list[Recommendation]:
    """Next best steps based on real progress, never jumping prerequisites."""
    paths = load_paths(db)
    recs: list[Recommendation] = []
    path_progress = {}
    for path in paths:
        pmap = progress_map(db, user_id, path)
        pp = compute_path_progress(path, pmap)
        path_progress[path.slug] = (path, pmap, pp)

    # Which paths are unlocked by prerequisite completion?
    unlocked = {}
    for slug, (path, pmap, pp) in path_progress.items():
        prereqs = path.prerequisites or []
        unmet = [p for p in prereqs if not (p in path_progress and path_progress[p][2].completed_all)]
        unlocked[slug] = unmet

    # 1. Revisit items flagged for review first
    review_rows = db.scalars(
        select(LearningActivityProgress)
        .where(LearningActivityProgress.user_id == user_id, LearningActivityProgress.state == "review")
    ).all()
    act_by_id: dict[int, LearningActivity] = {}
    if review_rows:
        ids = [r.activity_id for r in review_rows]
        acts = db.scalars(select(LearningActivity).where(LearningActivity.id.in_(ids))).all()
        act_by_id = {a.id: a for a in acts}
        slug_by_act = {}
        for slug, (path, pmap, pp) in path_progress.items():
            for m in path.modules:
                for u in m.units:
                    for a in u.activities:
                        slug_by_act[a.id] = slug
        for row in review_rows[:4]:
            act = act_by_id.get(row.activity_id)
            if not act:
                continue
            ps = slug_by_act.get(act.id, "")
            recs.append(Recommendation(
                kind="review",
                title=act.title,
                reason="Marcada para revisão por você",
                path_slug=ps,
                url=f"/learning-paths/{ps}?focus={act.id}",
                priority=1,
            ))

    # 2. Next unstarted activity, respecting module gates and path prerequisites
    for slug, (path, pmap, pp) in path_progress.items():
        if pp.completed_all:
            continue
        if unlocked[slug]:
            continue  # path locked by prerequisite, handled below
        for module in path.modules:
            if not module_gate_met(path, module, pp):
                continue
            mstate = pp.module_state[module.slug]
            if mstate["complete"]:
                continue
            for unit in module.units:
                for act in unit.activities:
                    state = pmap[act.id].state if act.id in pmap else "not_started"
                    if state == "completed":
                        continue
                    if act.gap:
                        recs.append(Recommendation(
                            kind="gap",
                            title=act.title,
                            reason=f"Lacuna de conteúdo: {act.gap}",
                            path_slug=slug,
                            url=f"/learning-paths/{slug}?focus={act.id}",
                            priority=60,
                        ))
                        continue
                    reason = (
                        "Continue de onde parou" if state == "in_progress"
                        else f"Próximo passo de {module.title}"
                    )
                    recs.append(Recommendation(
                        kind="next_activity",
                        title=act.title,
                        reason=reason,
                        path_slug=slug,
                        url=f"/learning-paths/{slug}?focus={act.id}",
                        priority=2 if state == "in_progress" else 5,
                    ))
                    break
                else:
                    continue
                break
            break

    # 3. Locked paths: explain what to finish first
    for slug, unmet in unlocked.items():
        if not unmet:
            continue
        path = path_progress[slug][0]
        titles = [path_progress[p][0].title for p in unmet if p in path_progress]
        if titles:
            recs.append(Recommendation(
                kind="prerequisite",
                title=f"{path.title} bloqueada",
                reason="Conclua primeiro: " + ", ".join(titles),
                path_slug=slug,
                url=f"/learning-paths/{slug}",
                priority=90,
            ))

    # 4. Unfinished labs in the catalog relevant to started paths
    lab_recs = _lab_recommendations(db, user_id, path_progress)
    recs.extend(lab_recs)

    recs.sort(key=lambda r: (r.priority, r.title))
    # de-duplicate by title+path
    seen = set()
    out = []
    for r in recs:
        k = (r.kind, r.path_slug, r.title)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= limit:
            break
    return out


def _lab_recommendations(db: Session, user_id: int, path_progress: dict) -> list[Recommendation]:
    """Suggest labs from paths already in progress whose challenge is unsolved."""
    done = {
        r.challenge_id
        for r in db.scalars(select(LabProgress).where(LabProgress.user_id == user_id)).all()
        if r.status == "completed"
    }
    out: list[Recommendation] = []
    for slug, (path, pmap, pp) in path_progress.items():
        if not pp.started or pp.completed_all:
            continue
        for module in path.modules:
            if not module_gate_met(path, module, pp):
                continue
            for unit in module.units:
                for act in unit.activities:
                    if act.kind != "lab" or not act.challenge_slug:
                        continue
                    state = pmap[act.id].state if act.id in pmap else "not_started"
                    if state == "completed":
                        continue
                    out.append(Recommendation(
                        kind="lab",
                        title=act.title,
                        reason=f"Laboratório pendente em {module.title}",
                        path_slug=slug,
                        url=f"/learning-paths/{slug}?focus={act.id}",
                        priority=40,
                    ))
                    break
                else:
                    continue
                break
            break
    return out[:3]


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

def certificate_ready(path: LearningPath, pp: PathProgress) -> bool:
    """All required activities done, including the capstone project."""
    return pp.completed_all and pp.completed > 0


def issue_certificate(db: Session, user_id: int, path: LearningPath, pp: PathProgress) -> LearningCertificate:
    existing = db.scalar(
        select(LearningCertificate).where(
            LearningCertificate.user_id == user_id, LearningCertificate.path_id == path.id
        )
    )
    if existing:
        existing.activities_completed = pp.completed
        existing.hours_logged = round(pp.minutes_done / 60)
        db.commit()
        return existing
    seed = f"{user_id}:{path.slug}:{utcnow().isoformat()}"
    serial = "RV-LP-" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
    cert = LearningCertificate(
        user_id=user_id,
        path_id=path.id,
        serial=serial,
        activities_completed=pp.completed,
        hours_logged=round(pp.minutes_done / 60),
    )
    db.add(cert)
    db.commit()
    return cert


def get_certificate(db: Session, user_id: int, path_id: int) -> LearningCertificate | None:
    return db.scalar(
        select(LearningCertificate).where(
            LearningCertificate.user_id == user_id, LearningCertificate.path_id == path_id
        )
    )