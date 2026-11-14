"""Importer for the HackTricks wiki (https://github.com/HackTricks-wiki/hacktricks).

Licence reality
---------------
HackTricks is published under **CC BY-NC 4.0** (``src/LICENSE.md``):
attribution is mandatory and use must be non-commercial. That is *not* a
permissive redistribution licence, so this importer is deliberately separate
from ``import_payloads_all_the_things`` and from the permissive licence gate:

* The source must be flagged ``noncommercial_reuse`` (not ``redistributable``).
* Every imported document carries a visible attribution block crediting
  Carlos Polop and linking the licence, plus our own non-commercial notice.

What the importer does
----------------------
1. Reads the mdBook tree under ``src/`` and uses ``SUMMARY.md`` as the
   authoritative hierarchy (title + nesting), so navigation mirrors upstream.
2. Strips the ``{{#include ...}}`` directives. The only include used is the
   training/ad banner; it is promotional, not content, so it is removed.
3. Rewrites relative links to other ``.md`` pages into in-app
   ``/kb/d/<slug>`` links; external links are left alone.
4. Localises referenced images into ``app/static/hacktricks/`` and rewrites the
   ``<img>`` sources to ``/static/hacktricks/...`` — the app's CSP only allows
   ``img-src 'self' data:``, so remote images would otherwise be blocked.
5. Records exact provenance (commit SHA, source path, source URL) per document.

The import is idempotent and never overwrites a human-reviewed body
(``apply_upstream_change`` rules).
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_import import git_commit, slugify
from .kb_models import KB_Category, KB_Document, KB_Reference, KB_Source
from .kb_sync import apply_upstream_change, sha256

SOURCE_SLUG = "hacktricks"

# Top-level HackTricks sections -> (RedVault group, Portuguese label).
# Anything unmapped falls into "advanced" so nothing is silently dropped.
SECTION_GROUPS: dict[str, tuple[str, str]] = {
    "welcome": ("reference", "HackTricks — Introdução"),
    "generic-methodologies-and-resources": ("reference", "Metodologias e recursos"),
    "privacy": ("reference", "Privacidade"),
    "generic-hacking": ("advanced", "Hacking genérico"),
    "linux-hardening": ("server", "Hardening de Linux"),
    "macos-hardening": ("server", "Hardening de macOS"),
    "windows-hardening": ("server", "Hardening de Windows"),
    "mobile-pentesting": ("advanced", "Pentest mobile"),
    "network-services-pentesting": ("server", "Pentest de serviços de rede"),
    "industrial-control-systems": ("advanced", "Sistemas de controle industrial (ICS/OT)"),
    "pentesting-web": ("web", "Pentest Web"),
    "blockchain": ("advanced", "Blockchain e contratos inteligentes"),
    "cloud-security": ("advanced", "Segurança em Cloud"),
    "hardware-physical-access": ("advanced", "Hardware e acesso físico"),
    "binary-exploitation": ("advanced", "Exploração binária"),
    "ai": ("advanced", "Segurança de IA"),
    "reversing": ("advanced", "Engenharia reversa"),
    "crypto": ("advanced", "Criptografia"),
    "stego": ("advanced", "Esteganografia"),
    "todo": ("reference", "TODO (upstream)"),
}

# Sections whose content should not be published as documents.
SKIP_SECTIONS = {"todo"}
# Files that live inside src/ but are not wiki pages.
SKIP_FILES = {"SUMMARY.md", "LICENSE.md"}

# Attribution block, one per language. The Portuguese text is prepended to the
# PT-BR edition (`pt` branch); the English one to the original `main` branch.
ATTRIBUTION_MD = (
    "> **Créditos:** conteúdo original de **HackTricks**, por **Carlos Polop** e "
    "contribuidores — <https://github.com/HackTricks-wiki/hacktricks>. "
    "Licenciado sob [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/): "
    "atribuição obrigatória e **uso não comercial**. Texto importado verbatim do "
    "commit `{sha}`; alterações locais são marcadas abaixo.\n\n"
)
ATTRIBUTION_MD_EN = (
    "> **Credits:** original content from **HackTricks**, by **Carlos Polop** and "
    "contributors — <https://github.com/HackTricks-wiki/hacktricks>. "
    "Licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/): "
    "attribution required and **non-commercial use only**. Text imported verbatim "
    "from commit `{sha}`; local changes are marked below.\n\n"
)

# Upstream branch -> (our language code, translation state). The wiki keeps a
# translated edition per language on its own branch; `pt` is Brazilian
# Portuguese. `main` is the English original.
BRANCH_LANGUAGES = {
    "pt": ("pt-BR", "translated"),
    "pt-br": ("pt-BR", "translated"),
    "main": ("en", "untranslated"),
    "master": ("en", "untranslated"),
}

SOURCE_URL_ROOT = "https://github.com/HackTricks-wiki/hacktricks/blob"

_INCLUDE_RE = re.compile(r"\{\{#include\s+([^}]+?)\s*\}\}")
_SUMMARY_LINK_RE = re.compile(r"^(\s*)-\s*\[(?P<title>[^\]]+)\]\((?P<path>[^)]+)\)")
_SUMMARY_HEAD_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
_MD_LINK_RE = re.compile(r"\]\((?P<target>[^)\s]+(?:#[^)\s]*)?)\)")
# Markdown image with an angle-bracket URL (the form upstream uses for paths
# containing spaces/parentheses), OR a plain URL. The plain form must allow
# balanced parentheses so "image (897).png" is matched whole, not truncated.
_IMG_INLINE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(<(?P<src>[^>]+)>\)"
    r"|!\[(?P<alt2>[^\]]*)\]\((?P<src2>(?:[^()]|\([^()]*\))+?)\)"
)
_HTML_IMG_RE = re.compile(r'<img(?P<attrs>[^>]*?)\bsrc="(?P<src>[^"]+)"(?P<rest>[^>]*)>', re.IGNORECASE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_heading(text: str) -> str:
    """Strip leading emoji and surrounding spaces from a SUMMARY heading."""
    text = re.sub(r"^[^\w\[]+", "", text.strip())
    return text.strip() or "Geral"


class SummaryNode:
    """One row of the upstream SUMMARY.md tree."""

    __slots__ = ("title", "path", "depth", "section")

    def __init__(self, title: str, path: str, depth: int, section: str):
        self.title = title
        self.path = path
        self.depth = depth
        self.section = section


def parse_summary(src: Path) -> tuple[list[tuple[str, str]], list[SummaryNode]]:
    """Return (sections, nodes) from SUMMARY.md.

    ``sections`` is the ordered list of (dir, title) top-level parts.
    ``nodes`` keeps every linked page with its nesting depth.
    """
    summary = src / "SUMMARY.md"
    sections: list[tuple[str, str]] = []
    nodes: list[SummaryNode] = []
    current_section = ""
    for raw in summary.read_text(encoding="utf-8").splitlines():
        head = _SUMMARY_HEAD_RE.match(raw)
        if head:
            current_section = _clean_heading(head.group("title"))
            continue
        link = _SUMMARY_LINK_RE.match(raw)
        if not link:
            continue
        path = link.group("path").split("#", 1)[0].strip()
        if not path.endswith(".md"):
            continue
        depth = (len(link.group(1)) - 2) // 2 if len(link.group(1)) >= 2 else 0
        depth = max(0, depth)
        section_dir = path.split("/", 1)[0] if "/" in path else ""
        if depth == 0 and section_dir and all(section_dir != d for d, _ in sections):
            sections.append((section_dir, current_section or section_dir))
        nodes.append(SummaryNode(link.group("title").strip(), path, depth, section_dir))
    return sections, nodes


def _is_external(target: str) -> bool:
    return bool(re.match(r"^(https?:|mailto:|#)", target))


def _normalise_image_src(src: str, md_path: Path, src_root: Path) -> Path | None:
    """Resolve a markdown image source to a real file inside the repo, if any."""
    src = src.strip()
    if _is_external(src):
        return None
    # Drop any title/angle-bracket leftovers and URL-decode %20.
    src = src.split('"', 1)[0].split("#", 1)[0].strip()
    src = src.replace("%20", " ")
    candidate = (md_path.parent / src).resolve()
    try:
        candidate.relative_to(src_root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class ImageStore:
    """Copy referenced images under ``app/static/hacktricks/`` once."""

    def __init__(self, target_root: Path):
        self.target_root = target_root

    def localise(self, source: Path, src_root: Path) -> str | None:
        try:
            rel = source.resolve().relative_to(src_root.resolve())
        except ValueError:
            return None
        dest = self.target_root / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        return "/static/hacktricks/" + quote(rel.as_posix(), safe="/")


def _rewrite_links(
    text: str, md_path: Path, src_root: Path, doc_slug_by_path: dict[str, str]
) -> str:
    """Rewrite relative ``.md`` links to in-app reader URLs.

    Links that do not resolve to an imported document are left untouched.
    """
    root = src_root.resolve()

    def replace(match: re.Match) -> str:
        target = match.group("target")
        if _is_external(target):
            return match.group(0)
        fragment = ""
        if "#" in target:
            target, fragment = target.split("#", 1)
            fragment = "#" + fragment
        if not target.endswith(".md"):
            return match.group(0)
        resolved = (md_path.parent / target).resolve()
        try:
            rel = resolved.relative_to(root).as_posix()
        except ValueError:
            return match.group(0)
        slug = doc_slug_by_path.get(rel)
        if slug:
            return f"](/kb/d/{slug}{fragment})"
        return match.group(0)

    return _MD_LINK_RE.sub(replace, text)


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def build_body(
    text: str,
    *,
    md_path: Path,
    src_root: Path,
    images: ImageStore,
    doc_slug_by_path: dict[str, str],
    sha: str,
    language: str = "pt-BR",
) -> str:
    """Clean one upstream markdown file for the reader."""
    # 1. Remove {{#include}} directives (training banners etc.).
    text = _INCLUDE_RE.sub("", text)

    # 2. Localise <img> tags (the banner uses them) and markdown images.
    def html_img(match: re.Match) -> str:
        src = match.group("src")
        local = None
        if not _is_external(src):
            resolved = _normalise_image_src(src, md_path, src_root)
            if resolved:
                local = images.localise(resolved, src_root)
        new_src = local or src
        return f'<img{match.group("attrs")}src="{new_src}"{match.group("rest")}>'

    text = _HTML_IMG_RE.sub(html_img, text)

    def md_img(match: re.Match) -> str:
        alt = match.group("alt") if match.group("src") is not None else match.group("alt2")
        src = match.group("src") if match.group("src") is not None else match.group("src2")
        local = None
        if not _is_external(src):
            resolved = _normalise_image_src(src, md_path, src_root)
            if resolved:
                local = images.localise(resolved, src_root)
        return f"![{alt}]({local or src})"

    text = _IMG_INLINE_RE.sub(md_img, text)

    # 3. Rewrite relative .md links to reader URLs.
    text = _rewrite_links(text, md_path, src_root, doc_slug_by_path)

    # 4. Prepend our own attribution block (not upstream text), in the
    #    document's own language.
    template = ATTRIBUTION_MD if language.startswith("pt") else ATTRIBUTION_MD_EN
    return _collapse_blank_lines(template.format(sha=sha[:12]) + text.strip() + "\n")


def hacktricks_slug(rel_path: str) -> str:
    """Stable, namespaced slug for an upstream relative path."""
    without_ext = rel_path[:-3] if rel_path.endswith(".md") else rel_path
    # A README.md documents its directory: use the directory name, not "readme".
    if without_ext.endswith("/README") or without_ext == "README":
        without_ext = without_ext[: -len("/README")] if without_ext != "README" else "index"
    return "ht-" + slugify(without_ext.replace("/", "-"))[:100]


def ensure_source(db: Session) -> KB_Source:
    """Register (or correct) the HackTricks source row."""
    source = db.scalar(select(KB_Source).where(KB_Source.slug == SOURCE_SLUG))
    if source is None:
        source = KB_Source(slug=SOURCE_SLUG)
        db.add(source)
    source.name = "HackTricks"
    source.repo_url = "https://github.com/HackTricks-wiki/hacktricks"
    source.license_name = "CC BY-NC 4.0"
    source.license_url = "https://creativecommons.org/licenses/by-nc/4.0/"
    source.author = "Carlos Polop e contribuidores"
    # Honest flags: not freely redistributable, but reusable for non-commercial
    # purposes with attribution (what we do here).
    source.redistributable = False
    source.noncommercial_reuse = True
    source.notes = (
        "CC BY-NC 4.0: requer atribuição e uso NÃO comercial. Importado verbatim "
        "para uso pessoal/educacional, com créditos ao autor e aviso de licença "
        "em cada documento. Não redistribua nem use este conteúdo em produto "
        "comercial sem autorização de Carlos Polop."
    )
    db.flush()
    return source


def _section_lookup(section_dir: str) -> tuple[str, str] | None:
    """Case-insensitive lookup (upstream has both ``AI`` and ``ai``)."""
    if section_dir in SECTION_GROUPS:
        return SECTION_GROUPS[section_dir]
    lowered = section_dir.lower()
    for key, value in SECTION_GROUPS.items():
        if key.lower() == lowered:
            return value
    return None


def _category_for_section(db: Session, section_dir: str, section_title: str, cache: dict) -> KB_Category:
    if section_dir in cache:
        return cache[section_dir]
    found = _section_lookup(section_dir)
    group, label = found if found else ("advanced", section_title or section_dir)
    slug = "ht-" + slugify(section_dir) if section_dir else "ht-root"
    cat = db.scalar(select(KB_Category).where(KB_Category.slug == slug))
    if cat is None:
        cat = KB_Category(slug=slug, title=f"HackTricks · {label}", group_name=group, sort_order=500)
        db.add(cat)
        db.flush()
    cache[section_dir] = cat
    return cat


def import_hacktricks(
    db: Session, root: Path, *, images_root: Path | None = None, language: str | None = None
) -> dict:
    """Import the whole HackTricks ``src/`` tree into the knowledge base.

    ``language`` overrides detection. Detection uses the checked-out branch:
    the wiki keeps translated editions on per-language branches (``pt`` is
    Brazilian Portuguese). Defaulting to the ``pt`` edition is why the caller
    should clone with ``--branch pt``.
    """
    src_root = root / "src" if (root / "src").is_dir() else root
    if not (src_root / "SUMMARY.md").is_file():
        raise ValueError(f"{src_root} não parece ser um clone do HackTricks (sem SUMMARY.md)")

    source = ensure_source(db)
    sha, branch = git_commit(root)
    source.commit_sha = sha
    source.branch = branch or "main"
    source.last_synced = _utcnow()
    source.last_checked = _utcnow()

    if language is None:
        language, translation_state = BRANCH_LANGUAGES.get(
            (branch or "").lower(), ("pt-BR", "translated")
        )
    else:
        translation_state = "translated" if language.startswith("pt") else "untranslated"

    licenses_dir = Path("content/kb_licenses")
    licenses_dir.mkdir(parents=True, exist_ok=True)
    license_file = src_root / "LICENSE.md"
    if license_file.is_file():
        (licenses_dir / "hacktricks-LICENSE.md").write_text(
            license_file.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
        )

    if images_root is None:
        images_root = Path(__file__).resolve().parent / "static" / "hacktricks"
    images = ImageStore(images_root)

    _sections, nodes = parse_summary(src_root)
    section_titles = dict(_sections)
    # Title by path: the SUMMARY title is curated, the file H1 is a fallback.
    summary_title = {node.path: node.title for node in nodes}
    section_of = {node.path: node.section for node in nodes}

    md_files = sorted(
        p.relative_to(src_root).as_posix()
        for p in src_root.rglob("*.md")
        if p.name not in SKIP_FILES
        and not any(part.startswith(".") for part in p.relative_to(src_root).parts)
    )
    # Skip non-content sections (todo dumps, banners).
    md_files = [p for p in md_files if p.split("/", 1)[0] not in SKIP_SECTIONS]

    slug_by_path = {rel: hacktricks_slug(rel) for rel in md_files}
    # Guard against slug collisions (two paths sanitising to the same value).
    seen: set[str] = set()
    for rel, slug in list(slug_by_path.items()):
        base = slug
        n = 2
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen.add(slug)
        slug_by_path[rel] = slug

    cat_cache: dict = {}
    stats = {"created": 0, "updated": 0, "flagged": 0, "skipped": 0, "categories": 0, "images": 0}
    before_images = set(images_root.rglob("*")) if images_root.exists() else set()

    for rel in md_files:
        md_path = src_root / rel
        raw = md_path.read_text(encoding="utf-8", errors="replace")
        if not raw.strip():
            stats["skipped"] += 1
            continue

        body = build_body(
            raw, md_path=md_path, src_root=src_root, images=images,
            doc_slug_by_path=slug_by_path, sha=sha, language=language,
        )
        digest = sha256(body)
        section_dir = section_of.get(rel) or (rel.split("/", 1)[0] if "/" in rel else "")
        section_title = section_titles.get(section_dir, "HackTricks")
        category = _category_for_section(db, section_dir, section_title or "HackTricks", cat_cache)

        existing = db.scalar(
            select(KB_Document).where(
                KB_Document.source_id == source.id, KB_Document.source_path == rel
            )
        )
        if existing:
            result = apply_upstream_change(existing, body)
            if result == "unchanged":
                stats["skipped"] += 1
            elif existing.translation_status == "reviewed":
                stats["flagged"] += 1
            else:
                stats["updated"] += 1
            continue

        # The `pt` edition translates page H1s but leaves SUMMARY nav labels in
        # English, so for PT we prefer the document's own heading. For English,
        # the SUMMARY title is the curated one.
        heading = _first_heading(raw)
        if language.startswith("pt"):
            title = heading or summary_title.get(rel) or md_path.stem
        else:
            title = summary_title.get(rel) or heading or md_path.stem
        doc = KB_Document(
            slug=slug_by_path[rel],
            title=title[:200],
            summary=_first_blockquote(raw),
            category_id=category.id,
            language=language,
            origin="imported",
            source_id=source.id,
            source_path=rel,
            source_url=f"{SOURCE_URL_ROOT}/{sha}/{quote(rel)}",
            source_commit=sha,
            translation_status=translation_state,
            review_status="pending",
            body_md=body,
            body_original_md=body,
            content_hash=digest,
            word_count=len(body.split()),
            tags="hacktricks " + (section_dir or ""),
            imported_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(doc)
        db.flush()
        db.add(
            KB_Reference(
                document_id=doc.id,
                title=f"HackTricks — {title}",
                organization="HackTricks (Carlos Polop)",
                url=f"https://hacktricks.wiki/pt/{rel[:-3].replace('/README', '')}.html"
                if language.startswith("pt")
                else f"https://hacktricks.wiki/en/{rel[:-3].replace('/README', '')}.html",
                kind="repository",
                verified=True,
                sort_order=10,
            )
        )
        stats["created"] += 1

    stats["categories"] = len(cat_cache)
    if images_root.exists():
        stats["images"] = len([p for p in images_root.rglob("*") if p.is_file()])

    db.flush()
    return stats


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _first_blockquote(text: str) -> str:
    """First meaningful blockquote line — skipping ``[!TIP]``-style callouts."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        content = stripped.lstrip(">").strip()
        if not content or content.startswith("[!") or content.startswith("!["):
            continue
        return content[:400]
    return ""