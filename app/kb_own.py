"""Import hand-written (own) knowledge base documents.

Own documents are authored for REDVAULT in pt-BR, under
``content/kb_own/*.md`` with YAML front matter, and carry ``origin='own'``.
Different from imported material, the text is ours and can be redistributed
freely; external facts are always attributed to a primary source in the
``references`` block, and the document states plainly what it does not cover.

This module only *binds* the document to the platform: it never writes content
it does not have.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_models import KB_Category, KB_Document, KB_Reference


OWN_DIR = Path(__file__).resolve().parent.parent / "content" / "kb_own"


def _parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"{path.name}: falta front matter")
    _, front, body = raw.split("---", 2)
    meta: dict = {"references": [], "tags": ""}
    current_list: list | None = None
    for line in front.strip().splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_list is not None:
            item = line[4:].strip().strip('"').strip("'")
            if current_list is meta["references"]:
                title, _, url = item.partition(" | ")
                current_list.append({"title": title.strip(), "url": url.strip()})
            else:
                current_list.append(item)
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value == "":
            meta[key] = []
            current_list = meta[key]
        else:
            meta[key] = value
            current_list = None
    meta["body_md"] = body.strip()
    meta["_path"] = path.name
    return meta


def load_own_documents(directory: Path | None = None) -> list[dict]:
    directory = directory or OWN_DIR
    if not directory.exists():
        return []
    docs = [_parse(p) for p in sorted(directory.glob("*.md"))]
    required = ("slug", "title", "category", "summary")
    for doc in docs:
        missing = [k for k in required if not doc.get(k)]
        if missing:
            raise ValueError(f"{doc['_path']}: front matter incompleto: {missing}")
    return docs


def sync_own_documents(db: Session) -> int:
    """Upsert own documents. Returns how many were written or updated."""
    docs = load_own_documents()
    written = 0
    now = datetime.now(timezone.utc)
    for doc in docs:
        category = db.scalar(select(KB_Category).where(KB_Category.slug == doc["category"]))
        if not category:
            raise ValueError(f"{doc['_path']}: categoria '{doc['category']}' não existe na KB")
        row = db.scalar(select(KB_Document).where(KB_Document.slug == doc["slug"]))
        body = doc["body_md"]
        content_hash = hashlib.sha256(body.encode()).hexdigest()[:32]
        if not row:
            row = KB_Document(slug=doc["slug"])
            db.add(row)
        row.title = doc["title"]
        row.summary = doc["summary"]
        row.category_id = category.id
        row.language = "pt-BR"
        row.origin = "own"
        row.source_path = doc["_path"]
        row.source_commit = ""
        row.translation_status = "translated"
        row.review_status = doc.get("review", "pending")
        row.body_md = body
        row.body_original_md = body
        row.content_hash = content_hash
        row.word_count = len(body.split())
        row.tags = doc.get("tags", "")
        row.cwe = doc.get("cwe", "")
        row.owasp = doc.get("owasp", "")
        row.severity = doc.get("severity", "")
        row.imported_at = now
        row.updated_at = now
        db.flush()

        # References are replaced wholesale so a corrected link always lands.
        for existing in db.scalars(select(KB_Reference).where(KB_Reference.document_id == row.id)).all():
            db.delete(existing)
        for i, ref in enumerate(doc["references"], 1):
            if not ref.get("url"):
                raise ValueError(f"{doc['_path']}: referência '{ref.get('title')}' sem URL")
            db.add(KB_Reference(
                document_id=row.id,
                title=ref["title"],
                organization=doc.get("organization", ""),
                url=ref["url"],
                kind=doc.get("ref_kind", "official"),
                verified=True,
                sort_order=i * 10,
            ))
        written += 1
    db.commit()
    return written