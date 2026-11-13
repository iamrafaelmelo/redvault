"""Link from a platform challenge to its knowledge-base documentation.

The mapping is explicit (challenge category/tags -> KB category slug). When a
challenge matches more than one document, the category root wins so the reader
lands on the overview rather than a database-specific page.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_models import KB_Category, KB_Document

# Platform challenge category (manifest "category") -> KB category slug.
CHALLENGE_CATEGORY_MAP = {
    "sqli": "sqli",
    "xss": "xss",
    "access": "idor",
    "auth": "authentication",
    "api": "api-security",
    "server": "command-injection",
    "client": "xss",
    "logic": "business-logic",
    "upload": "file-upload",
    "recon": "recon",
    "advanced": "chaining",
    "chain": "chaining",
    "cache": "cache-deception",
    "headers": "host-header",
    "deserialization": "deserialization",
    "ssrf": "ssrf",
    "xxe": "xxe",
    "ssti": "ssti",
    "file": "lfi",
    "jwt": "jwt",
    "graphql": "graphql",
    "race": "race-conditions",
    "smuggling": "request-smuggling",
    "csrf": "csrf",
}

# Tag fallbacks when the category is generic.
TAG_FALLBACKS = [
    ("ssrf", "ssrf"),
    ("xxe", "xxe"),
    ("ssti", "ssti"),
    ("jwt", "jwt"),
    ("graphql", "graphql"),
    ("sqli", "sqli"),
    ("xss", "xss"),
    ("lfi", "lfi"),
    ("command-injection", "command-injection"),
    ("upload", "file-upload"),
    ("deserialization", "deserialization"),
    ("mfa", "mfa-bypass"),
    ("open-redirect", "open-redirect"),
    ("cors", "cors"),
]


def kb_slug_for_challenge(category_slug: str, tags: list[str], tech: list[str]) -> str | None:
    lowered = {t.lower() for t in (tags or [])} | {t.lower() for t in (tech or [])}
    for tag, kb_slug in TAG_FALLBACKS:
        if tag in lowered:
            return kb_slug
    return CHALLENGE_CATEGORY_MAP.get((category_slug or "").lower())


def document_for_challenge(db: Session, category_slug: str, tags: list[str], tech: list[str]) -> KB_Document | None:
    """Best knowledge-base document for a challenge, or None when unmapped."""
    slug = kb_slug_for_challenge(category_slug, tags, tech)
    if not slug:
        return None
    category = db.scalar(select(KB_Category).where(KB_Category.slug == slug))
    if not category:
        return None
    # Prefer the imported/category-root overview: shortest title, own origin first.
    docs = db.scalars(select(KB_Document).where(KB_Document.category_id == category.id)).all()
    if not docs:
        return None

    def rank(doc: KB_Document) -> tuple:
        overview = 0 if doc.slug.endswith("readme") else 1
        return (overview, doc.origin != "imported", len(doc.title), doc.title)

    return sorted(docs, key=rank)[0]