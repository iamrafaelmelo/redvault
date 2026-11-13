"""Full-text search for the knowledge base, backed by SQLite FTS5.

Search must find words *inside* documents, not just in titles. SQLite ships
FTS5 in every modern build, so this adds no dependency.

The index is kept in sync by explicit calls after import/sync rather than by
triggers: imports are bulk operations, and rebuilding once at the end is much
cheaper than firing 140 trigger rows one by one.

`rebuild()` is idempotent and safe to call at startup.
"""
from __future__ import annotations

import re

from sqlalchemy import text

from .database import engine

_FTS_TABLE = "kb_search"
_TERM_RE = re.compile(r"[0-9A-Za-zÀ-ÿ_\-]{2,}")


def _fts_available(conn) -> bool:
    try:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)"))
        conn.execute(text("DROP TABLE IF EXISTS _fts_probe"))
        return True
    except Exception:  # noqa: BLE001 - depends on the SQLite build
        return False


def ensure_index() -> bool:
    """Create the FTS table when the build supports it. Returns availability."""
    with engine.begin() as conn:
        if not _fts_available(conn):
            return False
        conn.execute(
            text(
                f"""CREATE VIRTUAL TABLE IF NOT EXISTS {_FTS_TABLE} USING fts5(
                    slug UNINDEXED,
                    title,
                    summary,
                    body,
                    tags,
                    tokenize = 'unicode61 remove_diacritics 2'
                )"""
            )
        )
    return True


def rebuild() -> int:
    """Drop and repopulate the whole index. Returns the number of documents."""
    if not ensure_index():
        return 0
    from .database import SessionLocal
    from .kb_models import KB_Document

    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {_FTS_TABLE}"))

    count = 0
    with SessionLocal() as db:
        rows = db.query(KB_Document.slug, KB_Document.title, KB_Document.summary,
                        KB_Document.body_md, KB_Document.tags).all()
    with engine.begin() as conn:
        for slug, title, summary, body, tags in rows:
            conn.execute(
                text(
                    f"INSERT INTO {_FTS_TABLE} (slug, title, summary, body, tags) "
                    "VALUES (:slug, :title, :summary, :body, :tags)"
                ),
                {"slug": slug, "title": title or "", "summary": summary or "",
                 "body": body or "", "tags": (tags or "").replace("-", " ")},
            )
            count += 1
    return count


def _fts_query(raw: str) -> str:
    """Turn user input into a safe FTS5 query.

    Every term is quoted and prefix-matched, so ``'`` or ``AND`` in the input
    cannot break the query or be interpreted as an operator. Terms are ANDed:
    "ssrf php cloud" finds documents containing all three.
    """
    terms = _TERM_RE.findall(raw)
    if not terms:
        return ""
    return " AND ".join(f'"{term}"*' for term in terms)


def search(raw: str, limit: int = 60) -> list[dict]:
    """Return ranked hits: slug, title, summary and a short highlighted snippet."""
    query = _fts_query(raw)
    if not query or not ensure_index():
        return []
    with engine.begin() as conn:
        try:
            rows = conn.execute(
                text(
                    f"""SELECT slug, title, summary,
                               snippet({_FTS_TABLE}, 3, '«', '»', '…', 28) AS snip,
                               bm25({_FTS_TABLE}, 0.0, 10.0, 4.0, 1.0, 6.0) AS score
                        FROM {_FTS_TABLE}
                        WHERE {_FTS_TABLE} MATCH :q
                        ORDER BY score
                        LIMIT :limit"""
                ),
                {"q": query, "limit": limit},
            ).mappings().all()
        except Exception:  # noqa: BLE001 - malformed query must not 500 the page
            return []
    return [dict(row) for row in rows]