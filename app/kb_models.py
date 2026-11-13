"""Data model for the knowledge base (Academy 2.0).

Design goals:

* **Traceability.** Every imported document records where it came from: repo,
  license, author, branch, commit SHA, original path and import date. A document
  can always be traced to an exact commit of an upstream project.
* **Translation state.** Three states per document (`untranslated`,
  `translated`, `reviewed`). Imported text is never marked `reviewed`
  automatically.
* **Modular content.** Documents and payloads are one row per file/item, never
  a single giant JSON blob, so a sync can diff them one by one.
* **Interconnection.** Topics link to challenges, payloads, tools and other
  topics through explicit tables, not name matching at render time.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KB_Source(Base):
    """An upstream project the Academy imports from."""

    __tablename__ = "kb_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    repo_url: Mapped[str] = mapped_column(String(300))
    license_name: Mapped[str] = mapped_column(String(60), default="")
    license_url: Mapped[str] = mapped_column(String(300), default="")
    author: Mapped[str] = mapped_column(String(120), default="")
    # Whether the license actually allows redistribution into this project.
    redistributable: Mapped[bool] = mapped_column(Boolean, default=False)
    branch: Mapped[str] = mapped_column(String(60), default="main")
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="")

    documents: Mapped[list["KB_Document"]] = relationship(back_populates="source")


class KB_Category(Base):
    """Hierarchical navigation node (Web App Security > SQL Injection, ...)."""

    __tablename__ = "kb_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("kb_categories.id"), nullable=True)
    group_name: Mapped[str] = mapped_column(String(60), default="web")  # web|api|auth|server|client|files|advanced
    sort_order: Mapped[int] = mapped_column(Integer, default=100)

    parent: Mapped["KB_Category | None"] = relationship(remote_side="KB_Category.id")


class KB_Document(Base):
    """One page of the knowledge base.

    `origin` distinguishes our own writing from imported material:
      * ``own``       — written for REDVAULT, PT-BR, authored here.
      * ``imported``  — text imported from a redistributable source.
      * ``reference`` — our summary of a topic whose original is external and
                        not redistributable; the text is ours, the link is theirs.
    """

    __tablename__ = "kb_documents"
    __table_args__ = (UniqueConstraint("source_id", "source_path", name="uq_kb_doc_source_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")

    category_id: Mapped[int | None] = mapped_column(ForeignKey("kb_categories.id"))
    language: Mapped[str] = mapped_column(String(10), default="pt-BR")
    origin: Mapped[str] = mapped_column(String(20), default="own")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("kb_sources.id"), nullable=True)
    source_path: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(400), default="")
    source_commit: Mapped[str] = mapped_column(String(64), default="")

    translation_status: Mapped[str] = mapped_column(String(20), default="untranslated")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")

    body_md: Mapped[str] = mapped_column(Text, default="")
    body_original_md: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    cwe: Mapped[str] = mapped_column(String(200), default="")
    owasp: Mapped[str] = mapped_column(String(200), default="")
    severity: Mapped[str] = mapped_column(String(20), default="")
    tags: Mapped[str] = mapped_column(String(400), default="")  # space separated

    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped["KB_Source | None"] = relationship(back_populates="documents")
    category: Mapped["KB_Category | None"] = relationship()
    payloads: Mapped[list["KB_Payload"]] = relationship(back_populates="document")


class KB_Payload(Base):
    """A single payload, always tied to its parent document.

    Context is mandatory: a payload without `context` and `expected` is a
    snippet, not a payload entry, and must not be published.
    """

    __tablename__ = "kb_payloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True)
    # technique label, e.g. "Union-Based", "Time-Based", "Filter Bypass"
    technique: Mapped[str] = mapped_column(String(120), default="")
    code: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(30), default="text")
    description: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[str] = mapped_column(Text, default="")
    expected: Mapped[str] = mapped_column(Text, default="")
    limitations: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(String(400), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=100)

    document: Mapped["KB_Document"] = relationship(back_populates="payloads")


class KB_TopicLink(Base):
    """Explicit relation between a document and a challenge."""

    __tablename__ = "kb_topic_links"
    __table_args__ = (UniqueConstraint("document_id", "challenge_id", name="uq_kb_topic_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"))


class KB_RelatedDocument(Base):
    """Explicit 'see also' relation between two documents."""

    __tablename__ = "kb_related_documents"
    __table_args__ = (UniqueConstraint("document_id", "related_id", name="uq_kb_related"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"))
    related_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"))


class KB_Reference(Base):
    """External, verifiable source attached to a document."""

    __tablename__ = "kb_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(250))
    organization: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(400))
    # official | research | writeup | repository | educational | advisory
    kind: Mapped[str] = mapped_column(String(30), default="official")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)


class KB_Bookmark(Base):
    """Per-user favourites and recently read documents."""

    __tablename__ = "kb_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_kb_bookmark"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KB_Visit(Base):
    __tablename__ = "kb_visits"
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_kb_visit"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    visits: Mapped[int] = mapped_column(Integer, default=1)