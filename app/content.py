"""Content discovery, validation and seeding.

Each vulnerable lab owns a manifest.json. The platform core never needs to be
edited to add a lab: drop a directory with app.py + manifest.json and restart
(or run the content sync command).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import markdown as md
import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import (
    CATEGORY_META,
    CONTENT_DIR,
    DIFFICULTIES,
    DIFFICULTY_XP,
    LABS_DIR,
    SOURCE_TYPES,
)
from .models import (
    Achievement,
    Category,
    Challenge,
    Flag,
    Hint,
    Path,
    PathChallenge,
    Reference,
    Solution,
)


# ---------------------------------------------------------------------------
# Lab manifests
# ---------------------------------------------------------------------------

REQUIRED_MANIFEST_FIELDS = {
    "slug",
    "title",
    "summary",
    "category",
    "difficulty",
    "lab_dir",
    "flags",
    "hints",
    "solution",
    "references",
}


@dataclass
class ManifestError:
    path: Path
    message: str


def discover_manifests() -> tuple[list[dict], list[ManifestError]]:
    manifests: list[dict] = []
    errors: list[ManifestError] = []
    if not LABS_DIR.exists():
        return manifests, errors
    for path in sorted(LABS_DIR.glob("*/manifest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(ManifestError(path, f"Invalid JSON: {exc}"))
            continue
        data["_manifest_path"] = str(path)
        data["_lab_dir"] = path.parent.name
        issues = validate_manifest(data)
        if issues:
            errors.extend(ManifestError(path, issue) for issue in issues)
        manifests.append(data)
    return manifests, errors


def validate_manifest(data: dict) -> list[str]:
    issues: list[str] = []
    missing = REQUIRED_MANIFEST_FIELDS - set(data)
    if missing:
        issues.append(f"missing fields: {', '.join(sorted(missing))}")
        return issues
    slug = data.get("slug", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", slug):
        issues.append("slug must be lowercase kebab-case (3-80 chars)")
    if data.get("lab_dir") != data.get("_lab_dir"):
        issues.append("lab_dir must match the lab directory name")
    if data.get("category") not in CATEGORY_META:
        issues.append(f"unknown category: {data.get('category')}")
    if data.get("difficulty") not in DIFFICULTIES:
        issues.append(f"unknown difficulty: {data.get('difficulty')}")
    if data.get("kind", "challenge") not in {"challenge", "machine", "realistic"}:
        issues.append("kind must be challenge|machine|realistic")
    flags = data.get("flags") or []
    if not isinstance(flags, list) or not flags:
        issues.append("at least one flag is required")
    else:
        keys = [f.get("key") for f in flags]
        if len(keys) != len(set(keys)):
            issues.append("flag keys must be unique")
        for flag in flags:
            if flag.get("key") in {None, ""}:
                issues.append("flag key missing")
            if flag.get("flag_type", "user") not in {"user", "root", "api", "hidden", "bonus"}:
                issues.append(f"invalid flag_type for {flag.get('key')}")
    hints = data.get("hints") or []
    if not isinstance(hints, list) or len(hints) < 3:
        issues.append("at least 3 progressive hints are required")
    else:
        levels = [h.get("level") for h in hints]
        if levels != list(range(1, len(hints) + 1)):
            issues.append("hint levels must start at 1 and be sequential")
        for h in hints:
            if not h.get("body") or not h.get("title"):
                issues.append(f"hint {h.get('level')} needs title and body")
    solution = data.get("solution") or {}
    for field in ("walkthrough", "root_cause", "mitigation"):
        if not solution.get(field):
            issues.append(f"solution.{field} is required")
    refs = data.get("references") or []
    if not refs:
        issues.append("at least one reference is required")
    for ref in refs:
        if not str(ref.get("url", "")).startswith(("https://", "http://")):
            issues.append(f"invalid reference URL: {ref.get('url')}")
        if ref.get("source_type") and ref["source_type"] not in SOURCE_TYPES:
            issues.append(f"invalid source_type: {ref.get('source_type')}")
    return issues


def _clear_child_rows(db: Session, challenge: Challenge) -> None:
    for model in (Reference, Hint):
        db.execute(delete(model).where(model.challenge_id == challenge.id))
    db.execute(delete(Solution).where(Solution.challenge_id == challenge.id))
    db.execute(delete(Flag).where(Flag.challenge_id == challenge.id))
    db.flush()


def seed_platform_content(db: Session) -> dict:
    """Idempotently upsert categories, labs, paths and achievements."""
    categories = {}
    for index, (slug, (name, description, icon)) in enumerate(CATEGORY_META.items()):
        category = db.scalar(select(Category).where(Category.slug == slug))
        if not category:
            category = Category(slug=slug)
            db.add(category)
        category.name = name
        category.description = description
        category.icon = icon
        category.sort_order = index
        categories[slug] = category
    db.flush()

    manifests, errors = discover_manifests()
    seen_slugs: set[str] = set()
    for data in manifests:
        existing = db.scalar(select(Challenge).where(Challenge.slug == data["slug"]))
        challenge = existing or Challenge(slug=data["slug"])
        challenge.kind = data.get("kind", "challenge")
        challenge.title = data["title"]
        challenge.codename = data.get("codename", "")
        challenge.summary = data["summary"]
        challenge.category_id = categories[data["category"]].id
        challenge.difficulty = data["difficulty"]
        base_xp = data.get("xp") or DIFFICULTY_XP[data["difficulty"]]
        challenge.xp = int(base_xp)
        challenge.estimated_minutes = int(data.get("estimated_minutes", 20))
        challenge.lab_dir = data["lab_dir"]
        challenge.story_md = data.get("story", "")
        challenge.objective_md = data.get("objective", "")
        challenge.rules_md = data.get("rules", "")
        challenge.tech = data.get("tech", [])
        challenge.tags = data.get("tags", [])
        challenge.status = data.get("status", "published")
        challenge.sort_order = int(data.get("sort_order", 0))
        if not existing:
            db.add(challenge)
        db.flush()

        _clear_child_rows(db, challenge)
        for index, flag_data in enumerate(data["flags"]):
            db.add(
                Flag(
                    challenge_id=challenge.id,
                    key=flag_data["key"],
                    label=flag_data.get("label", flag_data["key"].title()),
                    flag_type=flag_data.get("flag_type", "user"),
                    points=int(flag_data.get("points", 25)),
                    required=bool(flag_data.get("required", True)),
                    requires_objective=bool(flag_data.get("requires_objective", False)),
                    sort_order=index,
                )
            )
        for hint_data in data["hints"]:
            db.add(
                Hint(
                    challenge_id=challenge.id,
                    level=int(hint_data["level"]),
                    title=hint_data["title"],
                    body_md=hint_data["body"],
                    cost=int(hint_data.get("cost", 10)),
                )
            )
        solution = data["solution"]
        db.add(
            Solution(
                challenge_id=challenge.id,
                walkthrough_md=solution["walkthrough"],
                root_cause_md=solution["root_cause"],
                mitigation_md=solution["mitigation"],
            )
        )
        for ref in data["references"]:
            db.add(
                Reference(
                    challenge_id=challenge.id,
                    title=ref["title"],
                    url=ref["url"],
                    source_type=ref.get("source_type", "official"),
                    description=ref.get("description", ""),
                )
            )
        seen_slugs.add(data["slug"])

    # Remove labs that no longer exist so the catalog reflects the filesystem.
    for challenge in db.scalars(select(Challenge)).all():
        if challenge.slug not in seen_slugs:
            db.delete(challenge)
    db.flush()

    seed_paths(db, seen_slugs)
    seed_achievements(db)
    db.commit()
    return {
        "challenges": len(manifests),
        "errors": [f"{e.path.name}: {e.message}" for e in errors],
    }


def seed_paths(db: Session, available_slugs: set[str]) -> None:
    path_file = CONTENT_DIR / "paths.json"
    if not path_file.exists():
        return
    data = json.loads(path_file.read_text(encoding="utf-8"))
    seen = set()
    for index, item in enumerate(data):
        path = db.scalar(select(Path).where(Path.slug == item["slug"]))
        if not path:
            path = Path(slug=item["slug"])
            db.add(path)
        path.title = item["title"]
        path.description = item.get("description", "")
        path.difficulty = item.get("difficulty", "beginner")
        path.estimated_hours = int(item.get("estimated_hours", 8))
        path.icon = item.get("icon", "route")
        path.prerequisites = item.get("prerequisites", [])
        path.sort_order = index
        db.flush()
        db.execute(delete(PathChallenge).where(PathChallenge.path_id == path.id))
        for position, slug in enumerate(item.get("challenges", [])):
            challenge = db.scalar(select(Challenge).where(Challenge.slug == slug))
            if challenge:
                db.add(PathChallenge(path_id=path.id, challenge_id=challenge.id, position=position))
        seen.add(path.slug)
    for path in db.scalars(select(Path)).all():
        if path.slug not in seen:
            db.delete(path)


ACHIEVEMENTS = [
    ("first-blood", "Primeiro Sangue", "Envie sua primeira flag correta.", "flag", 25, False),
    ("first-solve", "Cabeça de Ponte", "Conclua seu primeiro desafio.", "target", 50, False),
    ("five-solves", "Embalo", "Conclua cinco desafios.", "bolt", 100, False),
    ("fifteen-solves", "Operador Profundo", "Conclua quinze desafios.", "crosshair", 250, False),
    ("no-hints-5", "Sem Ajuda", "Conclua cinco desafios sem desbloquear nenhum hint.", "eye-off", 150, False),
    ("recon-master", "Cartógrafo", "Conclua todos os desafios publicados de Recon.", "radar", 200, False),
    ("auth-master", "Corretor de Identidades", "Conclua todos os desafios de Autenticação.", "key", 200, False),
    ("access-master", "Quebrador de Fronteiras", "Conclua todos os desafios de Controle de Acesso.", "lock", 200, False),
    ("sqli-master", "Sussurrador de Queries", "Conclua todos os desafios de SQL Injection.", "database", 200, False),
    ("xss-master", "Assassino de Contexto", "Conclua todos os desafios de XSS.", "code", 250, False),
    ("first-machine", "Root", "Envie todas as flags obrigatórias de uma máquina.", "skull", 300, False),
    ("insane-solve", "Contra as Probabilidades", "Conclua um desafio Insano.", "flame", 500, False),
    ("chain-solve", "Reação em Cadeia", "Conclua um cenário de Encadeamento de Vulnerabilidades.", "chain", 350, False),
    ("path-complete", "Metódico", "Conclua uma trilha de aprendizado inteira.", "route", 400, False),
    ("solution-seeker", "Revisão Pós-Ação", "Desbloqueie um walkthrough completo.", "book", 0, True),
]


def seed_achievements(db: Session) -> None:
    for index, (code, name, description, icon, xp_bonus, hidden) in enumerate(ACHIEVEMENTS):
        item = db.scalar(select(Achievement).where(Achievement.code == code))
        if not item:
            item = Achievement(code=code)
            db.add(item)
        item.name = name
        item.description = description
        item.icon = icon
        item.xp_bonus = xp_bonus
        item.hidden = hidden
        item.sort_order = index


# ---------------------------------------------------------------------------
# Academy markdown
# ---------------------------------------------------------------------------

_MD_EXTENSIONS = ["fenced_code", "tables", "toc", "sane_lists", "attr_list"]
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_cache: dict[str, tuple[float, dict]] = {}


def _read_article(path: Path) -> dict:
    mtime = path.stat().st_mtime
    cached = _cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    raw = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = raw
    match = _FRONTMATTER.match(raw)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = raw[match.end():]
    renderer = md.Markdown(extensions=_MD_EXTENSIONS)
    html = renderer.convert(body)
    toc = getattr(renderer, "toc", "") or ""
    article = {
        "slug": meta.get("slug", path.stem),
        "title": meta.get("title", path.stem.replace("-", " ").title()),
        "category": meta.get("category", "methods"),
        "difficulty": meta.get("difficulty", "beginner"),
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", []),
        "updated": str(meta.get("updated", "")),
        "version": str(meta.get("version", "")),
        "source_type": meta.get("source_type", "official"),
        "order": int(meta.get("order", 100)),
        "body_md": body,
        "html": html,
        "toc": toc,
        "reading_minutes": max(4, len(body.split()) // 180),
        "path": str(path),
    }
    _cache[str(path)] = (mtime, article)
    return article


def load_articles() -> list[dict]:
    folder = CONTENT_DIR / "academy"
    if not folder.exists():
        return []
    articles = [_read_article(p) for p in sorted(folder.glob("*.md"))]
    return sorted(articles, key=lambda a: (a["order"], a["title"]))


def get_article(slug: str) -> dict | None:
    for article in load_articles():
        if article["slug"] == slug:
            return article
    return None


def search_articles(query: str, category: str = "", difficulty: str = "") -> list[dict]:
    query = query.strip().lower()
    results = []
    for article in load_articles():
        if category and article["category"] != category:
            continue
        if difficulty and article["difficulty"] != difficulty:
            continue
        if query:
            haystack = " ".join(
                [article["title"], article["summary"], article["body_md"], " ".join(article["tags"])]
            ).lower()
            if query not in haystack:
                continue
        results.append(article)
    return results


def load_json_content(name: str, default):
    path = CONTENT_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))
