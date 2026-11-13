"""Synchronisation rules for imported documents.

These functions are pure (they take a DB session and plain values), so the
behaviour that matters — never losing human work — is testable without
cloning anything.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_models import KB_Document


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_upstream_change(document: KB_Document, new_text: str) -> str:
    """Update a document after its upstream file changed.

    Returns what happened: ``unchanged``, ``skipped`` (human-reviewed and
    untouched upstream) or ``flagged`` (upstream changed; review required).

    Rules:
      * A ``reviewed`` translation is never overwritten. We only record that the
        upstream moved on and mark it ``needs_review``.
      * An untranslated document is safe to refresh in place.
      * Anything else is flagged, never silently replaced.
    """
    new_hash = sha256(new_text)
    if document.content_hash == new_hash:
        return "unchanged"

    document.body_original_md = new_text
    document.content_hash = new_hash

    if document.translation_status == "reviewed":
        document.review_status = "needs_review"
        return "flagged"

    if document.translation_status == "untranslated":
        document.body_md = new_text
        document.word_count = len(new_text.split())
        return "flagged"

    # translated but not reviewed: keep the translation, flag the mismatch
    document.review_status = "needs_review"
    return "flagged"


def removed_upstream(db: Session, source_id: int, missing_paths: set[str]) -> list[KB_Document]:
    """Documents whose upstream file disappeared.

    They are *not* deleted — a human decided to keep them — but are marked so
    the operator can decide. Returns the affected rows.
    """
    affected = []
    for document in db.scalars(select(KB_Document).where(KB_Document.source_id == source_id)):
        if document.source_path in missing_paths:
            document.review_status = "upstream_removed"
            affected.append(document)
    return affected