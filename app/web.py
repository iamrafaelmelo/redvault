"""HTML application routes."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from .config import (
    CATEGORY_META,
    DIFFICULTIES,
    LAB_IDLE_TIMEOUT,
    LAB_MAX_LIFETIME,
    MAX_ACTIVE_LABS,
    SESSION_COOKIE,
    TEMPLATE_DIR,
    USE_BWRAP,
)
from .content import get_article, load_articles, load_json_content, search_articles
from .deps import common_context, get_db, render_markdown
from .lab_manager import lan_share_enabled, lab_manager, lab_url
from .models import (
    Achievement,
    Activity,
    AuthSession,
    Category,
    Challenge,
    FlagSubmission,
    Hint,
    HintUnlock,
    LabSession,
    ObjectiveState,
    Path,
    PathChallenge,
    Progress,
    User,
    UserAchievement,
)
from .security import (
    check_csrf,
    current_user,
    flash_cookie_name,
    get_session,
    local_session,
    set_flash,
)
from .services.progress import (
    path_progress,
    solved_flag_keys,
    stats_for,
    xp_total,
)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
router = APIRouter()

def flash_redirect(url: str, message: str, kind: str = "ok", status_code: int = 303) -> RedirectResponse:
    response = RedirectResponse(url, status_code=status_code)
    set_flash(response, [{"message": message, "kind": kind}])
    return response


def render(request: Request, db: Session, template: str, user: User | None, active: str, **context) -> HTMLResponse:
    data = common_context(request, db, user, active)
    data.update(context)
    return templates.TemplateResponse(request=request, name=template, context=data)


def get_challenge(db: Session, slug: str) -> Challenge | None:
    return db.scalar(
        select(Challenge)
        .options(
            selectinload(Challenge.category),
            selectinload(Challenge.flags),
            selectinload(Challenge.hints),
            selectinload(Challenge.solution),
            selectinload(Challenge.references),
        )
        .where(Challenge.slug == slug)
    )


# ---------------------------------------------------------------------------
# Legacy authentication URLs
# ---------------------------------------------------------------------------
# REDVAULT is a single-operator, loopback-only installation, so there is no
# login: every request is served as the local operator. These routes stay only
# so bookmarks and old links land on the dashboard instead of a 404.

@router.get("/login")
async def login_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/login")
async def login_submit_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.get("/setup")
async def setup_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/setup")
async def setup_submit_redirect() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    session = get_session(db, request.cookies.get(SESSION_COOKIE))
    if session:
        db.delete(session)
        db.commit()
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)

    stats = stats_for(db, user)
    challenges = db.scalars(
        select(Challenge).options(selectinload(Challenge.category)).where(Challenge.status == "published")
    ).all()
    progress_map = stats["progress_map"]
    recommended = [
        c
        for c in challenges
        if c.kind == "challenge" and c.id not in stats["completed_ids"]
    ]
    recommended.sort(key=lambda c: (DIFFICULTIES.index(c.difficulty), c.sort_order, c.title))
    next_up = recommended[:4]

    paths = db.scalars(select(Path).order_by(Path.sort_order)).all()
    path_cards = []
    for path in paths:
        prog = path_progress(db, user, path)
        if prog["total"]:
            path_cards.append({"path": path, "progress": prog})
    active_path = next((p for p in path_cards if 0 < p["progress"]["completed"] < p["progress"]["total"]), None)
    if not active_path and path_cards:
        active_path = path_cards[0]

    active_labs = []
    for lab in lab_manager.active_labs():
        if lab.user_id != user.id:
            continue
        challenge = db.get(Challenge, lab.challenge_id)
        if challenge:
            active_labs.append({"lab": lab, "challenge": challenge})

    recent_achievements = db.execute(
        select(Achievement, UserAchievement)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.unlocked_at.desc())
        .limit(3)
    ).all()

    return render(
        request,
        db,
        "dashboard.html",
        user,
        "dashboard",
        stats=stats,
        recommended=next_up,
        path_cards=path_cards,
        active_path=active_path,
        active_labs=active_labs,
        recent_achievements=recent_achievements,
        progress_map=progress_map,
    )


# ---------------------------------------------------------------------------
# Challenges and machines
# ---------------------------------------------------------------------------

def _catalog(db: Session, user: User, kind: str | None = None):
    query = select(Challenge).options(
        selectinload(Challenge.category),
        selectinload(Challenge.flags),
    ).where(Challenge.status == "published")
    if kind == "machines":
        query = query.where(Challenge.kind.in_(["machine", "realistic"]))
    elif kind == "challenges":
        query = query.where(Challenge.kind == "challenge")
    challenges = db.scalars(query).all()
    progress_rows = db.scalars(select(Progress).where(Progress.user_id == user.id)).all()
    progress_map = {p.challenge_id: p for p in progress_rows}
    solved = {
        row.challenge_id: set()
        for row in progress_rows
    }
    for row in db.scalars(
        select(FlagSubmission).where(FlagSubmission.user_id == user.id, FlagSubmission.status == "correct")
    ).all():
        solved.setdefault(row.challenge_id, set()).add(row.flag_key)
    return challenges, progress_map, solved


@router.get("/challenges", response_class=HTMLResponse)
async def challenges_index(
    request: Request,
    category: str = "",
    difficulty: str = "",
    state: str = "all",
    q: str = "",
    tag: str = "",
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/challenges", status_code=303)
    challenges, progress_map, solved = _catalog(db, user, kind="challenges")
    filtered = []
    for challenge in challenges:
        progress = progress_map.get(challenge.id)
        completed = bool(progress and progress.status == "completed")
        if category and not (challenge.category and challenge.category.slug == category):
            continue
        if difficulty and challenge.difficulty != difficulty:
            continue
        if state == "solved" and not completed:
            continue
        if state == "unsolved" and completed:
            continue
        if state == "progress" and not (progress and progress.status == "in_progress" and not completed):
            continue
        if tag and tag.lower() not in [str(t).lower() for t in (challenge.tags or [])]:
            continue
        if q:
            needle = q.lower()
            haystack = " ".join(
                [challenge.title, challenge.codename, challenge.summary, " ".join(challenge.tags or []), " ".join(challenge.tech or [])]
            ).lower()
            if needle not in haystack:
                continue
        filtered.append(challenge)
    filtered.sort(key=lambda c: (DIFFICULTIES.index(c.difficulty), c.sort_order, c.title))
    categories = db.scalars(select(Category).order_by(Category.sort_order)).all()
    category_counts = {
        c.slug: len([x for x in challenges if x.category_id == c.id]) for c in categories
    }
    completed_count = len([c for c in challenges if progress_map.get(c.id) and progress_map[c.id].status == "completed"])
    all_tags = sorted({str(t) for c in challenges for t in (c.tags or [])})
    return render(
        request, db, "challenges.html", user, "challenges",
        challenges=filtered, categories=categories, category_counts=category_counts,
        progress_map=progress_map, solved=solved, completed_count=completed_count,
        total_count=len(challenges), filters={"category": category, "difficulty": difficulty, "state": state, "q": q, "tag": tag},
        all_tags=all_tags,
    )


@router.get("/challenges/{slug}", response_class=HTMLResponse)
async def challenge_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/challenges/{slug}", status_code=303)
    challenge = get_challenge(db, slug)
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    if challenge.kind != "challenge":
        return RedirectResponse(f"/machines/{slug}", status_code=303)
    return _render_item(request, db, user, challenge, "challenges")


@router.get("/machines", response_class=HTMLResponse)
async def machines_index(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/machines", status_code=303)
    challenges, progress_map, solved = _catalog(db, user, kind="machines")
    challenges.sort(key=lambda c: (DIFFICULTIES.index(c.difficulty), c.sort_order))
    return render(
        request, db, "machines.html", user, "machines",
        machines=challenges, progress_map=progress_map, solved=solved,
    )


@router.get("/machines/{slug}", response_class=HTMLResponse)
async def machine_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/machines/{slug}", status_code=303)
    challenge = get_challenge(db, slug)
    if not challenge:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    if challenge.kind == "challenge":
        return RedirectResponse(f"/challenges/{slug}", status_code=303)
    return _render_item(request, db, user, challenge, "machines")


def _render_item(request: Request, db: Session, user: User, challenge: Challenge, active: str, lab_mode: bool = False):
    progress = db.scalar(select(Progress).where(Progress.user_id == user.id, Progress.challenge_id == challenge.id))
    if not progress:
        progress = Progress(user_id=user.id, challenge_id=challenge.id)
        db.add(progress)
        db.commit()
    unlocked_hints = set(
        db.scalars(
            select(HintUnlock.hint_id)
            .join(Hint, Hint.id == HintUnlock.hint_id)
            .where(HintUnlock.user_id == user.id, Hint.challenge_id == challenge.id)
        ).all()
    )
    solved = solved_flag_keys(db, user.id, challenge.id)
    objective_states = {
        state.flag_key: state
        for state in db.scalars(
            select(ObjectiveState).where(ObjectiveState.user_id == user.id, ObjectiveState.challenge_id == challenge.id)
        ).all()
    }
    latest_lab = lab_manager.active_for(user.id, challenge.id)
    lab_row = None
    if latest_lab:
        from .models import LabSession

        lab_row = db.get(LabSession, latest_lab.session_id)
    submissions = db.scalars(
        select(FlagSubmission)
        .where(FlagSubmission.user_id == user.id, FlagSubmission.challenge_id == challenge.id)
        .order_by(FlagSubmission.created_at.desc())
        .limit(8)
    ).all()
    all_hints_unlocked = len(unlocked_hints) >= len(challenge.hints)
    required = [f for f in challenge.flags if f.required]
    completed = progress.status == "completed"
    return render(
        request, db, "challenge_detail.html", user, active,
        challenge=challenge, progress=progress, unlocked_hints=unlocked_hints,
        solved_flags=solved, objective_states=objective_states, lab=lab_row,
        lab_url=lab_url(lab_row.port) if lab_row else "",
        lan_share=lan_share_enabled(),
        lab_lifetime_minutes=LAB_MAX_LIFETIME // 60,
        lab_idle_minutes=LAB_IDLE_TIMEOUT // 60,
        submissions=submissions, all_hints_unlocked=all_hints_unlocked,
        required_flags=required, completed=completed,
        remaining_required=[f for f in required if f.key not in solved],
        lab_mode=lab_mode,
    )


# ---------------------------------------------------------------------------
# Dedicated challenge page (full-screen, no dashboard chrome)
# ---------------------------------------------------------------------------

@router.get("/lab/{slug}", response_class=HTMLResponse)
async def lab_page(request: Request, slug: str, db: Session = Depends(get_db)):
    """Standalone page for one target, the way a TryHackMe room opens.

    Same content and controls as the panel detail view, rendered full screen
    with its own top bar so each challenge feels like a separate room.
    """
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/lab/{slug}", status_code=303)
    challenge = get_challenge(db, slug)
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    active = "machines" if challenge.kind != "challenge" else "challenges"
    return _render_item(request, db, user, challenge, active, lab_mode=True)


# ---------------------------------------------------------------------------
# Learning paths
# ---------------------------------------------------------------------------

@router.get("/paths", response_class=HTMLResponse)
async def paths_index(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/paths", status_code=303)
    paths = db.scalars(select(Path).order_by(Path.sort_order)).all()
    cards = []
    for path in paths:
        prog = path_progress(db, user, path)
        cards.append({"path": path, "progress": prog})
    return render(request, db, "paths.html", user, "paths", cards=cards)


@router.get("/paths/{slug}", response_class=HTMLResponse)
async def path_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/paths/{slug}", status_code=303)
    path = db.scalar(select(Path).options(selectinload(Path.items).selectinload(PathChallenge.challenge)).where(Path.slug == slug))
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    progress = path_progress(db, user, path)
    items = []
    progress_rows = {
        p.challenge_id: p for p in db.scalars(select(Progress).where(Progress.user_id == user.id)).all()
    }
    for item in path.items:
        items.append(
            {
                "item": item,
                "challenge": item.challenge,
                "done": item.challenge_id in progress["done_ids"],
                "progress": progress_rows.get(item.challenge_id),
            }
        )
    prereq_paths = []
    if path.prerequisites:
        prereq_paths = db.scalars(select(Path).where(Path.slug.in_(path.prerequisites))).all()
    all_paths = db.scalars(select(Path).order_by(Path.sort_order)).all()
    related = [p for p in all_paths if p.id != path.id][:3]
    return render(
        request, db, "path_detail.html", user, "paths",
        path=path, progress=progress, items=items, prereq_paths=prereq_paths, related=related,
    )


# ---------------------------------------------------------------------------
# Academy
# ---------------------------------------------------------------------------

ACADEMY_CATEGORIES = {
    "recon": "Recon & Discovery",
    "auth": "Authentication",
    "access": "Access Control",
    "sqli": "SQL Injection",
    "xss": "Cross-Site Scripting",
    "server": "Server-Side Attacks",
    "api": "API Security",
    "logic": "Business Logic",
    "upload": "File Upload",
    "client": "Client-Side Security",
    "advanced": "Advanced Web Attacks",
    "chain": "Vulnerability Chaining",
    "methods": "Methodology",
    "tools": "Tooling",
    "reference": "Reference",
}


@router.get("/academy", response_class=HTMLResponse)
async def academy_index(
    request: Request,
    q: str = "",
    category: str = "",
    difficulty: str = "",
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/academy", status_code=303)
    articles = search_articles(q, category, difficulty)
    all_articles = load_articles()
    categories = []
    for key, label in ACADEMY_CATEGORIES.items():
        count = len([a for a in all_articles if a["category"] == key])
        if count:
            categories.append({"key": key, "label": label, "count": count})
    return render(
        request, db, "academy.html", user, "academy",
        articles=articles, categories=categories, filters={"q": q, "category": category, "difficulty": difficulty},
        total=len(all_articles),
    )


@router.get("/academy/tools", response_class=HTMLResponse)
async def tools_index(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/academy/tools", status_code=303)
    tools = load_json_content("tools.json", [])
    grouped = {}
    for tool in tools:
        grouped.setdefault(tool.get("category", "Other"), []).append(tool)
    return render(request, db, "tools.html", user, "academy", tools=tools, grouped=grouped)


@router.get("/academy/quick-reference", response_class=HTMLResponse)
async def quick_reference(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/academy/quick-reference", status_code=303)
    article = get_article("quick-reference")
    if not article:
        raise HTTPException(status_code=404, detail="Referência rápida não encontrada")
    return render(request, db, "article.html", user, "academy", article=article, related=[])


@router.get("/academy/glossary", response_class=HTMLResponse)
async def glossary(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/academy/glossary", status_code=303)
    terms = load_json_content("glossary.json", [])
    grouped = {}
    for term in terms:
        grouped.setdefault(term["term"][0].upper(), []).append(term)
    return render(request, db, "glossary.html", user, "academy", grouped=grouped, terms=terms)


@router.get("/academy/cves", response_class=HTMLResponse)
async def cves(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/academy/cves", status_code=303)
    items = load_json_content("cves.json", [])
    return render(request, db, "cves.html", user, "academy", cves=items)


@router.get("/academy/{slug}", response_class=HTMLResponse)
async def academy_article(request: Request, slug: str, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/academy/{slug}", status_code=303)
    article = get_article(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    related = [a for a in load_articles() if a["category"] == article["category"] and a["slug"] != slug][:4]
    return render(request, db, "article.html", user, "academy", article=article, related=related)


# ---------------------------------------------------------------------------
# Profile, environments, settings
# ---------------------------------------------------------------------------

@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/profile", status_code=303)
    stats = stats_for(db, user)
    achievements = db.scalars(select(Achievement).order_by(Achievement.sort_order)).all()
    owned = {
        ua.achievement_id: ua
        for ua in db.scalars(select(UserAchievement).where(UserAchievement.user_id == user.id)).all()
    }
    submissions = db.execute(
        select(FlagSubmission, Challenge)
        .join(Challenge, Challenge.id == FlagSubmission.challenge_id)
        .where(FlagSubmission.user_id == user.id)
        .order_by(FlagSubmission.created_at.desc())
        .limit(60)
    ).all()
    hint_rows = db.execute(
        select(Hint, Challenge, HintUnlock)
        .join(Challenge, Challenge.id == Hint.challenge_id)
        .join(HintUnlock, HintUnlock.hint_id == Hint.id)
        .where(HintUnlock.user_id == user.id)
        .order_by(HintUnlock.created_at.desc())
        .limit(40)
    ).all()
    paths = db.scalars(select(Path).order_by(Path.sort_order)).all()
    path_cards = [{"path": p, "progress": path_progress(db, user, p)} for p in paths]
    return render(
        request, db, "profile.html", user, "profile",
        stats=stats, achievements=achievements, owned=owned,
        submissions=submissions, hint_rows=hint_rows, path_cards=path_cards,
    )


@router.get("/profile/export")
async def export_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    stats = stats_for(db, user)
    progress_rows = db.scalars(
        select(Progress).options(selectinload(Progress.challenge)).where(Progress.user_id == user.id)
    ).all()
    submissions = db.scalars(select(FlagSubmission).where(FlagSubmission.user_id == user.id)).all()
    owned = db.execute(
        select(Achievement.code)
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user.id)
    ).all()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {"username": user.username, "display_name": user.display_name, "created_at": user.created_at.isoformat()},
        "xp": xp_total(db, user.id),
        "progress": [
            {
                "challenge": p.challenge.slug,
                "title": p.challenge.title,
                "status": p.status,
                "hints_used": p.hints_used,
                "xp_awarded": p.xp_awarded,
                "time_spent_seconds": p.time_spent_seconds,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                "notes": p.notes,
            }
            for p in progress_rows
        ],
        "submissions": [
            {"challenge_id": s.challenge_id, "flag_key": s.flag_key, "status": s.status, "created_at": s.created_at.isoformat()}
            for s in submissions
        ],
        "achievements": [row[0] for row in owned],
        "summary": {k: v for k, v in stats.items() if k not in {"progress_map", "completed_ids", "recent_activity", "category_stats", "difficulty_stats", "activity_14d", "mastered_categories", "weakest_categories"}},
    }
    response = JSONResponse(payload)
    response.headers["Content-Disposition"] = 'attachment; filename="redvault-progress.json"'
    return response


def _lab_view(db: Session) -> dict:
    active = lab_manager.active_labs()
    challenges = {c.id: c for c in db.scalars(select(Challenge)).all()}
    rows = []
    for lab in active:
        row = db.get(LabSession, lab.session_id)
        challenge = challenges.get(lab.challenge_id)
        if challenge:
            rows.append({"lab": lab, "row": row, "challenge": challenge})
    return {"active": rows, "max": MAX_ACTIVE_LABS}


@router.get("/environments", response_class=HTMLResponse)
async def environments(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/environments", status_code=303)
    from .bot import bot_status

    lab_view = _lab_view(db)
    history = db.execute(
        select(LabSession, Challenge)
        .join(Challenge, Challenge.id == LabSession.challenge_id)
        .where(LabSession.user_id == user.id)
        .order_by(LabSession.started_at.desc())
        .limit(24)
    ).all()
    return render(
        request, db, "environments.html", user, "environments",
        active_labs=lab_view["active"], max_labs=MAX_ACTIVE_LABS,
        history=history, bot=bot_status(), bwrap=USE_BWRAP,
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login?next=/settings", status_code=303)
    stats = stats_for(db, user)
    return render(request, db, "settings.html", user, "settings", stats=stats)


@router.post("/settings/profile")
async def update_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    display_name = str(form.get("display_name", "")).strip()[:80] or user.username
    user.display_name = display_name
    db.commit()
    return flash_redirect("/settings", "Perfil atualizado.", "ok")


@router.post("/settings/session")
async def rotate_session(request: Request, db: Session = Depends(get_db)):
    """Issue a fresh CSRF token and revoke the other browser sessions."""
    user = current_user(request, db)
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()
    local_session(db, request)
    return flash_redirect("/settings", "Sessão rotacionada. Os outros navegadores foram desconectados.", "ok")


@router.post("/settings/reset")
async def reset_progress(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    confirm = str(form.get("confirm", "")).strip()
    if confirm != "RESET MY LAB":
        return flash_redirect("/settings", 'Frase de confirmação não confere. Digite "RESET MY LAB".', "error")
    from .models import LabSession

    for row in db.scalars(select(LabSession).where(LabSession.user_id == user.id, LabSession.status.in_(["running", "starting"]))).all():
        lab_manager.stop(db, row, clear_objectives=True)
    for model in (FlagSubmission, HintUnlock, ObjectiveState, Activity, UserAchievement, Progress):
        db.execute(delete(model).where(model.user_id == user.id))
    db.commit()
    return flash_redirect("/", "Todo o progresso pessoal foi apagado. O conteúdo dos labs continua disponível.", "ok")
