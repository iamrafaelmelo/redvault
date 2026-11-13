"""JSON API used by the UI."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .content import search_articles
from .deps import get_db, get_user, render_markdown
from .flags import derive_flag, flag_hash, mask_value, validate_flag
from .lab_manager import LabError, lab_manager, lab_url
from .models import (
    Activity,
    Challenge,
    Challenge as ChallengeModel,
    Flag,
    FlagSubmission,
    Hint,
    HintUnlock,
    LabSession,
    ObjectiveState,
    Progress,
    User,
)
from .security import check_csrf
from .services.progress import (
    award_completion,
    ensure_progress,
    evaluate_achievements,
    record_hint_use,
    solved_flag_keys,
    unlock_solution,
    xp_total,
)

router = APIRouter(prefix="/api")


def _challenge(db: Session, slug: str) -> Challenge:
    challenge = db.scalar(
        select(Challenge)
        .options(
            selectinload(Challenge.flags),
            selectinload(Challenge.hints),
            selectinload(Challenge.solution),
            selectinload(Challenge.category),
        )
        .where(Challenge.slug == slug)
    )
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    return challenge


def _payload(db: Session, user: User, challenge: Challenge) -> dict:
    row = db.scalar(
        select(LabSession)
        .where(
            LabSession.user_id == user.id,
            LabSession.challenge_id == challenge.id,
            LabSession.status.in_(["running", "starting"]),
        )
        .order_by(LabSession.id.desc())
    )
    active = lab_manager.active_for(user.id, challenge.id)
    if row and not active:
        row.status = "stopped"
        db.commit()
        row = None
    progress = db.scalar(select(Progress).where(Progress.user_id == user.id, Progress.challenge_id == challenge.id))
    return {
        "active": bool(row),
        "status": row.status if row else "stopped",
        "port": row.port if row else None,
        "url": lab_url(row.port) if row else "",
        "started_at": row.started_at.isoformat() if row else None,
        "reset_count": row.reset_count if row else 0,
        "challenge": {"slug": challenge.slug, "title": challenge.title, "kind": challenge.kind},
        "progress": {
            "status": progress.status if progress else "not_started",
            "xp_awarded": progress.xp_awarded if progress else 0,
            "hints_used": progress.hints_used if progress else 0,
            "time_spent_seconds": progress.time_spent_seconds if progress else 0,
        },
    }


@router.get("/challenges/{slug}/status")
def lab_status(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    challenge = _challenge(db, slug)
    lab = lab_manager.active_for(user.id, challenge.id)
    if lab:
        lab_manager.touch(lab.session_id)
    return _payload(db, user, challenge)


@router.post("/challenges/{slug}/start")
def start_lab(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    if challenge.status != "published":
        raise HTTPException(status_code=404, detail="Desafio indisponível")
    ensure_progress(db, user.id, challenge.id)
    try:
        row = lab_manager.start(db, user, challenge)
    except LabError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.add(
        Activity(
            user_id=user.id,
            kind="lab_started",
            message=f"Iniciou {challenge.title}",
            challenge_id=challenge.id,
            meta={"port": row.port},
        )
    )
    db.commit()
    return _payload(db, user, challenge)


@router.post("/challenges/{slug}/stop")
def stop_lab(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    stopped = lab_manager.stop_user_challenge(db, user.id, challenge.id)
    if stopped:
        db.add(
            Activity(
                user_id=user.id,
                kind="lab_stopped",
                message=f"Parou {challenge.title}",
                challenge_id=challenge.id,
            )
        )
        db.commit()
    return {"ok": True, "stopped": stopped, **_payload(db, user, challenge)}


@router.post("/challenges/{slug}/reset")
def reset_lab(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    try:
        row = lab_manager.reset(db, user, challenge)
    except LabError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.add(
        Activity(
            user_id=user.id,
            kind="lab_reset",
            message=f"Reiniciou {challenge.title} em estado limpo",
            challenge_id=challenge.id,
        )
    )
    db.commit()
    return _payload(db, user, challenge)


@router.get("/labs")
def active_labs(request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    labs = []
    for lab in lab_manager.active_labs():
        if lab.user_id != user.id:
            continue
        challenge = db.get(Challenge, lab.challenge_id)
        if not challenge:
            continue
        labs.append(
            {
                "slug": challenge.slug,
                "title": challenge.title,
                "port": lab.port,
                "url": lab_url(lab.port),
                "pid": lab.process.pid,
                "challenge_id": challenge.id,
            }
        )
    return {"labs": labs}


@router.post("/challenges/{slug}/hints/{level}")
async def unlock_hint(slug: str, level: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    hint = db.scalar(select(Hint).where(Hint.challenge_id == challenge.id, Hint.level == level))
    if not hint:
        raise HTTPException(status_code=404, detail="Hint não encontrado")
    newly = record_hint_use(db, user, challenge, hint)
    db.commit()
    progress = db.scalar(select(Progress).where(Progress.user_id == user.id, Progress.challenge_id == challenge.id))
    return {
        "ok": True,
        "newly_unlocked": newly,
        "level": hint.level,
        "title": hint.title,
        "cost": hint.cost,
        "body": str(render_markdown(hint.body_md)),
        "hints_used": progress.hints_used if progress else 0,
        "hint_penalty": progress.hint_penalty if progress else 0,
    }


@router.post("/challenges/{slug}/solution")
async def open_solution(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    ok, message = unlock_solution(db, user, challenge)
    db.commit()
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    solution = challenge.solution
    return {
        "ok": True,
        "message": message,
        "walkthrough": str(render_markdown(solution.walkthrough_md)) if solution else "",
        "root_cause": str(render_markdown(solution.root_cause_md)) if solution else "",
        "mitigation": str(render_markdown(solution.mitigation_md)) if solution else "",
    }


@router.post("/challenges/{slug}/flags")
async def submit_flag(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Corpo JSON inválido") from exc
    key = str(body.get("flag_key", "")).strip()
    value = str(body.get("value", "")).strip()
    if not key or not value:
        raise HTTPException(status_code=400, detail="flag_key e value são obrigatórios")
    if len(value) > 200:
        raise HTTPException(status_code=400, detail="Valor da flag muito longo")
    challenge = _challenge(db, slug)
    flag = next((f for f in challenge.flags if f.key == key), None)
    if not flag:
        raise HTTPException(status_code=404, detail="Slot de flag não encontrado")

    already = db.scalar(
        select(FlagSubmission).where(
            FlagSubmission.user_id == user.id,
            FlagSubmission.challenge_id == challenge.id,
            FlagSubmission.flag_key == key,
            FlagSubmission.status == "correct",
        )
    )
    if already:
        return {
            "ok": True,
            "correct": True,
            "duplicate": True,
            "message": "Esta flag já foi aceita.",
            "completed": _is_complete(db, user.id, challenge),
        }

    correct, message = validate_flag(db, user.id, challenge, flag, value)
    progress = ensure_progress(db, user.id, challenge.id)
    progress.attempts += 1
    db.flush()
    submission = FlagSubmission(
        user_id=user.id,
        challenge_id=challenge.id,
        flag_id=flag.id,
        flag_key=flag.key,
        value_hash=flag_hash(value),
        value_masked=mask_value(value),
        status="correct" if correct else "incorrect",
        ip=request.client.host if request.client else None,
    )
    db.add(submission)
    if correct:
        db.add(
            Activity(
                user_id=user.id,
                kind="flag_accepted",
                message=f"Capturou {flag.label} em {challenge.title}",
                challenge_id=challenge.id,
                meta={"flag_type": flag.flag_type},
            )
        )
    db.flush()
    newly_completed = False
    xp_awarded = 0
    unlocked = []
    if correct:
        # Completion (XP + achievements + activity) is owned by award_completion.
        # Calling evaluate_achievements again would drop the ones just awarded.
        newly_completed, xp_awarded, unlocked = award_completion(db, user, challenge)
    db.commit()
    found = solved_flag_keys(db, user.id, challenge.id)
    remaining = [f.label for f in challenge.flags if f.required and f.key not in found]
    return {
        "ok": True,
        "correct": correct,
        "message": message,
        "completed": _is_complete(db, user.id, challenge),
        "newly_completed": newly_completed,
        "xp_awarded": xp_awarded,
        "xp_total": xp_total(db, user.id),
        "remaining": remaining,
        "achievements": unlocked,
        "flag": {"key": flag.key, "label": flag.label, "type": flag.flag_type},
    }


def _is_complete(db: Session, user_id: int, challenge: Challenge) -> bool:
    progress = db.scalar(select(Progress).where(Progress.user_id == user_id, Progress.challenge_id == challenge.id))
    return bool(progress and progress.status == "completed")


@router.post("/challenges/{slug}/heartbeat")
async def heartbeat(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    try:
        body = await request.json()
    except Exception:
        body = {}
    seconds = int(body.get("seconds", 30) or 0)
    seconds = max(0, min(seconds, 120))
    progress = ensure_progress(db, user.id, challenge.id)
    if progress.status != "completed":
        progress.time_spent_seconds += seconds
        db.commit()
    return {"ok": True, "time_spent_seconds": progress.time_spent_seconds}


@router.post("/challenges/{slug}/notes")
async def save_notes(slug: str, request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    check_csrf(request)
    challenge = _challenge(db, slug)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Corpo JSON inválido") from exc
    notes = str(body.get("notes", ""))[:8000]
    progress = ensure_progress(db, user.id, challenge.id)
    progress.notes = notes
    db.commit()
    return {"ok": True, "length": len(notes)}


@router.get("/search")
def search(q: str, db: Session = Depends(get_db), user: User = Depends(get_user)):
    q = q.strip()
    if len(q) < 2:
        return {"challenges": [], "articles": []}
    needle = f"%{q.lower()}%"
    challenges = db.scalars(
        select(Challenge)
        .options(selectinload(Challenge.category))
        .where(
            Challenge.status == "published",
            Challenge.title.ilike(needle) | Challenge.summary.ilike(needle) | Challenge.codename.ilike(needle),
        )
        .limit(8)
    ).all()
    articles = search_articles(q)[:6]
    return {
        "challenges": [
            {
                "title": c.title,
                "slug": c.slug,
                "difficulty": c.difficulty,
                "url": f"/machines/{c.slug}" if c.kind != "challenge" else f"/challenges/{c.slug}",
                "category": c.category.name if c.category else "",
            }
            for c in challenges
        ],
        "articles": [
            {"title": a["title"], "slug": a["slug"], "url": f"/academy/{a['slug']}", "category": a["category"]}
            for a in articles
        ],
    }
