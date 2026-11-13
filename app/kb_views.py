"""Knowledge base (Academy 2.0) presentation logic.

Routes are registered on the platform router and live under ``/kb``:

    /kb                      library home: groups, categories, recent, search
    /kb/c/{slug}             category listing (hierarchical breadcrumbs)
    /kb/d/{slug}             document reader (TOC, payloads, links, references)
    /kb/payloads             payload library, filterable by technique/language
    /kb/sources              source registry: licence, commit, sync state

Everything reads from the ``kb_*`` tables; no content is hard-coded here.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import markdown as md
from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .deps import common_context, get_db
from .kb_models import (
    KB_Bookmark,
    KB_Category,
    KB_Document,
    KB_Payload,
    KB_Reference,
    KB_RelatedDocument,
    KB_Source,
    KB_TopicLink,
    KB_Visit,
)
from .kb_search import search as fts_search
from .models import Challenge
from .security import current_user

GROUPS = [
    ("web", "Web Application Security"),
    ("api", "API Security"),
    ("auth", "Authentication & Session"),
    ("server", "Server-Side Attacks"),
    ("client", "Client-Side Attacks"),
    ("files", "Files & Data Exposure"),
    ("advanced", "Advanced Exploitation"),
    ("reference", "Referência externa"),
]

_MD = md.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists", "attr_list", "codehilite"],
                  extension_configs={"codehilite": {"noclasses": True, "guess_lang": False}})


# The first <li> of a generated TOC is the document H1 itself. The reader
# already renders that title in its own header, so the duplicate is removed and
# the sub-sections are promoted to the top level of the sidebar.
def _prune_toc_root(toc_html: str) -> str:
    """Drop the duplicated H1 entry and promote its children one level up.

    The markdown renderer emits the document H1 as the TOC root; the reader
    shows that title in its own header, so repeating it in the sidebar is noise.
    Documents that already start at H2 are left untouched.
    """
    if not toc_html or "<li>" not in toc_html:
        return ""
    opening = toc_html.find("<ul>")
    closing = toc_html.rfind("</ul>")
    if opening == -1 or closing < opening:
        return ""
    items = toc_html[opening + 4:closing].strip()
    if "<li>" not in items:
        return ""
    # The H1 entry is: <li><a ...>Title</a><ul>children</ul></li>
    # When there are no children it is a bare <li>...</li> with no <ul>.
    nested = items.find("<ul>", items.find("</a>"))
    if nested == -1:
        if items.count("<li>") == 1:
            return ""  # only the title: nothing else to navigate
        return toc_html  # flat list of real sections
    root_tail = items.rfind("</ul>")
    # Children live between the nested <ul> and its matching </ul>, which is the
    # last one before the root </li>.
    root_li_end = items.find("</li>", root_tail)
    children = items[nested + 4:root_tail] if root_li_end != -1 else ""
    rest = items[root_li_end + 5:] if root_li_end != -1 else ""
    if not children.strip():
        return ""
    return f"<div class=\"toc\">\n<ul>\n{children.strip()}{rest.strip()}\n</ul>\n</div>"


def render_markdown(text: str) -> tuple[str, str]:
    """(html, toc_html) for a document body."""
    renderer = md.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists", "attr_list",
                                       "codehilite", "md_in_html"],
                           extension_configs={"codehilite": {"noclasses": True, "guess_lang": False}})
    html = renderer.convert(text or "")
    return html, _prune_toc_root(getattr(renderer, "toc", ""))


def _user(request: Request, db: Session):
    return current_user(request, db)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

def library_home(request: Request, db: Session, q: str = "", group: str = "", tag: str = "") -> HTMLResponse:
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login?next=/kb", status_code=303)

    categories = db.scalars(select(KB_Category).order_by(KB_Category.sort_order, KB_Category.title)).all()
    counts: dict[int, int] = {}
    for doc in db.scalars(select(KB_Document)).all():
        counts[doc.category_id] = counts.get(doc.category_id, 0) + 1

    total_docs = len(db.scalars(select(KB_Document.id)).all())

    results = fts_search(q) if q.strip() else []
    recent = db.execute(
        select(KB_Visit, KB_Document)
        .join(KB_Document, KB_Document.id == KB_Visit.document_id)
        .where(KB_Visit.user_id == user.id)
        .order_by(KB_Visit.last_seen.desc())
        .limit(6)
    ).all()
    favourites = db.execute(
        select(KB_Document)
        .join(KB_Bookmark, KB_Bookmark.document_id == KB_Document.id)
        .where(KB_Bookmark.user_id == user.id)
        .order_by(KB_Bookmark.created_at.desc())
        .limit(8)
    ).scalars().all()

    # Only categories that actually have documents are listed: an empty card
    # with a zero counter is noise, not information. Empty groups collapse too.
    grouped: dict[str, list[dict]] = {key: [] for key, _label in GROUPS}
    for cat in categories:
        count = counts.get(cat.id, 0)
        if count == 0:
            continue
        if group and cat.group_name != group:
            continue
        grouped.setdefault(cat.group_name, []).append(
            {"category": cat, "count": count}
        )

    # Documents matching the active tag, when one is selected.
    tagged = []
    if tag:
        tagged = db.scalars(
            select(KB_Document).where(KB_Document.tags.like(f"%{tag}%")).order_by(KB_Document.title).limit(60)
        ).all()

    return _render(
        request, db, user, "kb_index.html",
        grouped=grouped, groups=GROUPS, total=total_docs,
        q=q, group=group, tag=tag, results=results,
        recent=[{"doc": doc, "visit": visit} for visit, doc in recent],
        favourites=favourites,
    )


def _render(request, db, user, template, **context) -> HTMLResponse:
    from .web import templates

    data = common_context(request, db, user, "academy")
    data.update(context)
    return templates.TemplateResponse(request=request, name=template, context=data)


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

def category_page(request: Request, db: Session, slug: str) -> HTMLResponse:
    user = _user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/kb/c/{slug}", status_code=303)
    category = db.scalar(select(KB_Category).where(KB_Category.slug == slug))
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    documents = db.scalars(
        select(KB_Document).where(KB_Document.category_id == category.id).order_by(KB_Document.title)
    ).all()
    breadcrumbs = []
    node = category
    while node is not None:
        breadcrumbs.insert(0, node)
        node = db.get(KB_Category, node.parent_id) if node.parent_id else None
    return _render(
        request, db, user, "kb_category.html",
        category=category, documents=documents, breadcrumbs=breadcrumbs,
        group_label=dict(GROUPS).get(category.group_name, category.group_name),
    )


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

def document_page(request: Request, db: Session, slug: str) -> HTMLResponse:
    user = _user(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/kb/d/{slug}", status_code=303)
    doc = db.scalar(
        select(KB_Document)
        .options(selectinload(KB_Document.payloads), selectinload(KB_Document.category))
        .where(KB_Document.slug == slug)
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    html, toc = render_markdown(doc.body_md)

    references = db.scalars(
        select(KB_Reference).where(KB_Reference.document_id == doc.id).order_by(KB_Reference.sort_order)
    ).all()
    related = db.execute(
        select(KB_Document)
        .join(KB_RelatedDocument, KB_RelatedDocument.related_id == KB_Document.id)
        .where(KB_RelatedDocument.document_id == doc.id)
    ).scalars().all()
    # Also offer siblings from the same category, so nothing is an island.
    siblings = [
        d for d in db.scalars(
            select(KB_Document).where(KB_Document.category_id == doc.category_id, KB_Document.id != doc.id)
        ).all()
    ][:6]
    challenges = db.execute(
        select(Challenge)
        .join(KB_TopicLink, KB_TopicLink.challenge_id == Challenge.id)
        .where(KB_TopicLink.document_id == doc.id)
    ).scalars().all()
    source = db.get(KB_Source, doc.source_id) if doc.source_id else None
    bookmarked = db.scalar(
        select(KB_Bookmark).where(KB_Bookmark.user_id == user.id, KB_Bookmark.document_id == doc.id)
    )

    # Track the visit (recently read).
    visit = db.scalar(select(KB_Visit).where(KB_Visit.user_id == user.id, KB_Visit.document_id == doc.id))
    now = datetime.now(timezone.utc)
    if visit:
        visit.last_seen = now
        visit.visits += 1
    else:
        db.add(KB_Visit(user_id=user.id, document_id=doc.id, last_seen=now))
    db.commit()

    payloads = sorted(doc.payloads, key=lambda p: (p.sort_order, p.technique))
    return _render(
        request, db, user, "kb_document.html",
        doc=doc, html=html, toc=toc, references=references, related=related,
        siblings=siblings, challenges=challenges, source=source,
        bookmarked=bool(bookmarked), payloads=payloads,
    )


def toggle_bookmark(request: Request, db: Session, slug: str) -> RedirectResponse:
    user = _user(request, db)
    doc = db.scalar(select(KB_Document).where(KB_Document.slug == slug))
    if not user or not doc:
        raise HTTPException(status_code=404)
    existing = db.scalar(
        select(KB_Bookmark).where(KB_Bookmark.user_id == user.id, KB_Bookmark.document_id == doc.id)
    )
    if existing:
        db.delete(existing)
    else:
        db.add(KB_Bookmark(user_id=user.id, document_id=doc.id))
    db.commit()
    return RedirectResponse(f"/kb/d/{slug}#top", status_code=303)


# ---------------------------------------------------------------------------
# Payload library
# ---------------------------------------------------------------------------

PAGE_SIZE = 40


def payload_library(
    request: Request, db: Session, q: str = "", language: str = "", technique: str = "", page: int = 1
) -> HTMLResponse:
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login?next=/kb/payloads", status_code=303)
    query = (
        select(KB_Payload)
        .options(selectinload(KB_Payload.document))
        .join(KB_Document, KB_Document.id == KB_Payload.document_id)
    )
    if q.strip():
        query = query.where(KB_Payload.code.ilike(f"%{q.strip()}%") | KB_Payload.description.ilike(f"%{q.strip()}%"))
    if language:
        query = query.where(KB_Payload.language == language)
    if technique:
        query = query.where(KB_Payload.technique == technique)

    # A payload library grows to hundreds of entries: render one page at a time
    # instead of hundreds of <pre> blocks in a single response.
    total = len(db.scalars(query.with_only_columns(KB_Payload.id)).all())
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(max(1, page), pages)
    payloads = db.scalars(
        query.order_by(KB_Payload.technique, KB_Payload.sort_order).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()

    languages = db.execute(select(KB_Payload.language).distinct().order_by(KB_Payload.language)).scalars().all()
    techniques = db.execute(select(KB_Payload.technique).distinct().order_by(KB_Payload.technique)).scalars().all()

    def page_url(target: int) -> str:
        from urllib.parse import urlencode

        params = {"q": q, "language": language, "technique": technique, "page": target}
        return "/kb/payloads?" + urlencode({k: v for k, v in params.items() if v and not (k == "page" and v == 1)})

    return _render(
        request, db, user, "kb_payloads.html",
        payloads=payloads, languages=[l for l in languages if l], techniques=[t for t in techniques if t],
        filters={"q": q, "language": language, "technique": technique},
        total=total, page=page, pages=pages, page_url=page_url, page_size=PAGE_SIZE,
    )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def sources_page(request: Request, db: Session) -> HTMLResponse:
    user = _user(request, db)
    if not user:
        return RedirectResponse("/login?next=/kb/sources", status_code=303)
    sources = db.scalars(select(KB_Source).order_by(KB_Source.name)).all()
    rows = []
    for source in sources:
        doc_count = len(db.scalars(select(KB_Document.id).where(KB_Document.source_id == source.id)).all())
        rows.append({"source": source, "documents": doc_count})
    return _render(request, db, user, "kb_sources.html", rows=rows)