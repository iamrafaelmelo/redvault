"""Progress, XP, achievements and aggregate statistics."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import CATEGORY_META, DIFFICULTIES, DIFFICULTY_LABELS, level_for_xp
from ..models import (
    Achievement,
    Activity,
    Category,
    Challenge,
    Flag,
    FlagSubmission,
    Hint,
    HintUnlock,
    Path,
    PathChallenge,
    Progress,
    User,
    UserAchievement,
)


def xp_total(db: Session, user_id: int) -> int:
    progress_xp = db.scalar(select(func.coalesce(func.sum(Progress.xp_awarded), 0)).where(Progress.user_id == user_id)) or 0
    achievement_xp = db.scalar(
        select(func.coalesce(func.sum(Achievement.xp_bonus), 0))
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(UserAchievement.user_id == user_id)
    ) or 0
    return int(progress_xp + achievement_xp)


def solved_flag_keys(db: Session, user_id: int, challenge_id: int) -> set[str]:
    rows = db.scalars(
        select(FlagSubmission.flag_key).where(
            FlagSubmission.user_id == user_id,
            FlagSubmission.challenge_id == challenge_id,
            FlagSubmission.status == "correct",
        )
    ).all()
    return set(rows)


def required_flags(challenge: Challenge) -> list[Flag]:
    return [flag for flag in challenge.flags if flag.required]


def challenge_completed(db: Session, user_id: int, challenge: Challenge) -> bool:
    progress = db.scalar(select(Progress).where(Progress.user_id == user_id, Progress.challenge_id == challenge.id))
    return bool(progress and progress.status == "completed")


def get_progress(db: Session, user_id: int, challenge_id: int) -> Progress | None:
    return db.scalar(select(Progress).where(Progress.user_id == user_id, Progress.challenge_id == challenge_id))


def ensure_progress(db: Session, user_id: int, challenge_id: int) -> Progress:
    progress = get_progress(db, user_id, challenge_id)
    if not progress:
        progress = Progress(user_id=user_id, challenge_id=challenge_id)
        db.add(progress)
        db.flush()
    return progress


def award_completion(db: Session, user: User, challenge: Challenge) -> tuple[bool, int, list[str]]:
    """Award XP once when every required flag is correct.

    Returns ``(newly_completed, xp, achievement_names)`` where the names are the
    achievements unlocked by this completion (empty for repeat submissions).
    """
    progress = ensure_progress(db, user.id, challenge.id)
    if progress.status == "completed":
        return False, 0, []
    found = solved_flag_keys(db, user.id, challenge.id)
    if not all(flag.key in found for flag in required_flags(challenge)):
        return False, 0, []
    penalty = progress.hint_penalty or 0
    award = max(int(challenge.xp * 0.25), challenge.xp - penalty)
    if progress.hints_used == 0:
        award = int(award * 1.25)
    if progress.solution_unlocked:
        award = max(int(challenge.xp * 0.2), int(award * 0.5))
    progress.xp_awarded = max(10, award)
    progress.status = "completed"
    progress.completed_at = datetime.now(timezone.utc)
    progress.completed_without_hints = progress.hints_used == 0
    db.add(
        Activity(
            user_id=user.id,
            kind="challenge_completed",
            message=f"Concluiu {challenge.title}",
            challenge_id=challenge.id,
            meta={"xp": progress.xp_awarded, "difficulty": challenge.difficulty},
        )
    )
    db.flush()
    unlocked = [achievement.name for achievement in evaluate_achievements(db, user)]
    return True, progress.xp_awarded, unlocked


def record_hint_use(db: Session, user: User, challenge: Challenge, hint: Hint) -> bool:
    existing = db.scalar(select(HintUnlock).where(HintUnlock.user_id == user.id, HintUnlock.hint_id == hint.id))
    if existing:
        return False
    db.add(HintUnlock(user_id=user.id, hint_id=hint.id))
    progress = ensure_progress(db, user.id, challenge.id)
    progress.hints_used += 1
    progress.hint_penalty += hint.cost
    db.add(
        Activity(
            user_id=user.id,
            kind="hint_unlocked",
            message=f"Desbloqueou o hint {hint.level} de {challenge.title}",
            challenge_id=challenge.id,
            meta={"level": hint.level, "cost": hint.cost},
        )
    )
    db.flush()
    return True


def unlock_solution(db: Session, user: User, challenge: Challenge) -> tuple[bool, str]:
    progress = ensure_progress(db, user.id, challenge.id)
    if progress.solution_unlocked:
        return True, "Walkthrough já desbloqueado."
    total_hints = db.scalar(select(func.count(Hint.id)).where(Hint.challenge_id == challenge.id)) or 0
    unlocked = db.scalar(
        select(func.count(HintUnlock.id))
        .join(Hint, Hint.id == HintUnlock.hint_id)
        .where(HintUnlock.user_id == user.id, Hint.challenge_id == challenge.id)
    ) or 0
    if progress.status != "completed" and total_hints and unlocked < total_hints:
        return False, f"Desbloqueie todos os {total_hints} hints antes de pedir o walkthrough completo."
    progress.solution_unlocked = True
    db.add(
        Activity(
            user_id=user.id,
            kind="solution_unlocked",
            message=f"Abriu o walkthrough de {challenge.title}",
            challenge_id=challenge.id,
        )
    )
    evaluate_achievements(db, user)
    db.flush()
    return True, "Walkthrough desbloqueado. O XP deste desafio será reduzido se você concluir depois."


def stats_for(db: Session, user: User) -> dict:
    challenges = db.scalars(select(Challenge).where(Challenge.status == "published")).all()
    progress_rows = db.scalars(select(Progress).where(Progress.user_id == user.id)).all()
    progress_map = {p.challenge_id: p for p in progress_rows}
    completed = [c for c in challenges if progress_map.get(c.id) and progress_map[c.id].status == "completed"]
    machines = [c for c in challenges if c.kind in {"machine", "realistic"}]
    challenges_only = [c for c in challenges if c.kind == "challenge"]
    completed_machines = [c for c in machines if c in completed]
    total_xp = xp_total(db, user.id)
    level, title, floor, next_floor, description = level_for_xp(total_xp)
    xp_into = total_xp - floor
    xp_need = max(1, next_floor - floor) if next_floor > floor else 1
    hints_used = sum(p.hints_used for p in progress_rows)
    time_spent = sum(p.time_spent_seconds for p in progress_rows)
    submissions_ok = db.scalar(
        select(func.count(FlagSubmission.id)).where(FlagSubmission.user_id == user.id, FlagSubmission.status == "correct")
    ) or 0
    submissions_total = db.scalar(
        select(func.count(FlagSubmission.id)).where(FlagSubmission.user_id == user.id)
    ) or 0
    no_hint = sum(1 for c in completed if progress_map[c.id].completed_without_hints)

    categories = db.scalars(select(Category).order_by(Category.sort_order)).all()
    category_stats = []
    for category in categories:
        items = [c for c in challenges if c.category_id == category.id]
        if not items:
            continue
        done = [c for c in items if c in completed]
        pct = round(len(done) / len(items) * 100)
        category_stats.append(
            {
                "slug": category.slug,
                "name": category.name,
                "icon": category.icon,
                "total": len(items),
                "completed": len(done),
                "percent": pct,
                "mastered": pct >= 80,
            }
        )
    mastered = [c for c in category_stats if c["mastered"]]
    weakest = sorted([c for c in category_stats if c["completed"] > 0], key=lambda c: c["percent"])[:3]

    difficulty_stats = []
    for difficulty in DIFFICULTIES:
        items = [c for c in challenges_only if c.difficulty == difficulty]
        done = [c for c in items if c in completed]
        difficulty_stats.append(
            {
                "key": difficulty,
                "label": DIFFICULTY_LABELS[difficulty],
                "total": len(items),
                "completed": len(done),
                "percent": round(len(done) / len(items) * 100) if items else 0,
            }
        )

    last_14 = []
    today = datetime.now(timezone.utc).date()
    for days_ago in range(13, -1, -1):
        day = today - timedelta(days=days_ago)
        count = sum(
            1
            for c in completed
            if progress_map[c.id].completed_at
            and (progress_map[c.id].completed_at.date() == day)
        )
        last_14.append({"date": day.isoformat(), "count": count, "label": day.strftime("%d/%m")})

    recent = db.scalars(
        select(Activity).where(Activity.user_id == user.id).order_by(Activity.created_at.desc()).limit(12)
    ).all()

    first_solves = db.scalars(select(Progress).where(Progress.user_id == user.id, Progress.status == "completed")).all()
    avg_minutes = round((sum(p.time_spent_seconds for p in first_solves) / len(first_solves) / 60), 1) if first_solves else 0

    return {
        "total_challenges": len(challenges_only),
        "completed_challenges": len([c for c in completed if c.kind == "challenge"]),
        "total_machines": len(machines),
        "completed_machines": len(completed_machines),
        "total_items": len(challenges),
        "completed_items": len(completed),
        "completion_rate": round(len(completed) / len(challenges) * 100) if challenges else 0,
        "xp": total_xp,
        "level": level,
        "level_title": title,
        "level_description": description,
        "level_floor": floor,
        "level_next": next_floor,
        "level_percent": min(100, round(xp_into / xp_need * 100)),
        "hints_used": hints_used,
        "time_spent_seconds": time_spent,
        "submissions_correct": submissions_ok,
        "submissions_total": submissions_total,
        "accuracy": round(submissions_ok / submissions_total * 100) if submissions_total else 0,
        "no_hint_solves": no_hint,
        "category_stats": category_stats,
        "mastered_categories": mastered,
        "weakest_categories": weakest,
        "difficulty_stats": difficulty_stats,
        "activity_14d": last_14,
        "recent_activity": recent,
        "avg_minutes": avg_minutes,
        "progress_map": progress_map,
        "completed_ids": {c.id for c in completed},
    }


def path_progress(db: Session, user: User, path: Path) -> dict:
    item_rows = db.scalars(select(PathChallenge).where(PathChallenge.path_id == path.id).order_by(PathChallenge.position)).all()
    challenge_ids = [row.challenge_id for row in item_rows]
    completed = db.scalars(
        select(Progress.challenge_id).where(
            Progress.user_id == user.id,
            Progress.challenge_id.in_(challenge_ids),
            Progress.status == "completed",
        )
    ).all()
    done = set(completed)
    return {
        "total": len(challenge_ids),
        "completed": len(done),
        "percent": round(len(done) / len(challenge_ids) * 100) if challenge_ids else 0,
        "done_ids": done,
        "items": item_rows,
    }


def evaluate_achievements(db: Session, user: User) -> list[Achievement]:
    """Award achievements that are now true. Idempotent."""
    all_achievements = db.scalars(select(Achievement)).all()
    owned_ids = set(
        db.scalars(select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)).all()
    )
    progress_rows = db.scalars(select(Progress).where(Progress.user_id == user.id)).all()
    completed = [p for p in progress_rows if p.status == "completed"]
    completed_challenges = db.scalars(
        select(Challenge)
        .join(Progress, Progress.challenge_id == Challenge.id)
        .where(Progress.user_id == user.id, Progress.status == "completed")
    ).all()

    def by_category(slug: str) -> tuple[int, int]:
        total = db.scalar(
            select(func.count(Challenge.id))
            .join(Category, Challenge.category_id == Category.id)
            .where(Category.slug == slug, Challenge.status == "published", Challenge.kind == "challenge")
        ) or 0
        done = len([c for c in completed_challenges if c.category and c.category.slug == slug])
        return total, done

    def condition(code: str) -> bool:
        if code == "first-blood":
            return (
                db.scalar(
                    select(func.count(FlagSubmission.id)).where(
                        FlagSubmission.user_id == user.id, FlagSubmission.status == "correct"
                    )
                )
                or 0
            ) >= 1
        if code == "first-solve":
            return len(completed_challenges) >= 1
        if code == "five-solves":
            return len(completed_challenges) >= 5
        if code == "fifteen-solves":
            return len(completed_challenges) >= 15
        if code == "no-hints-5":
            return sum(1 for p in completed if p.completed_without_hints) >= 5
        if code.endswith("-master"):
            slug = {"recon-master": "recon", "auth-master": "auth", "access-master": "access", "sqli-master": "sqli", "xss-master": "xss"}[code]
            total, done = by_category(slug)
            return total > 0 and done >= total
        if code == "first-machine":
            machines = db.scalars(
                select(Challenge).where(Challenge.kind.in_(["machine", "realistic"]), Challenge.status == "published")
            ).all()
            return any(m.id in {c.id for c in completed_challenges} for m in machines)
        if code == "insane-solve":
            return any(c.difficulty == "insane" for c in completed_challenges)
        if code == "chain-solve":
            return any(c.category and c.category.slug == "chain" for c in completed_challenges)
        if code == "path-complete":
            for path in db.scalars(select(Path)).all():
                progress = path_progress(db, user, path)
                if progress["total"] and progress["completed"] == progress["total"]:
                    return True
            return False
        if code == "solution-seeker":
            return any(p.solution_unlocked for p in progress_rows)
        return False

    newly: list[Achievement] = []
    for achievement in all_achievements:
        if achievement.id in owned_ids:
            continue
        if condition(achievement.code):
            # Flush immediately: every later condition reads the database
            # (submissions, progress rows) and some, like ``level-five``, also
            # consume the achievements awarded here.
            db.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
            db.flush()
            db.add(
                Activity(
                    user_id=user.id,
                    kind="achievement",
                    message=f"Conquista desbloqueada: {achievement.name}",
                    meta={"code": achievement.code, "xp": achievement.xp_bonus},
                )
            )
            newly.append(achievement)
    if newly:
        db.flush()
    return newly
