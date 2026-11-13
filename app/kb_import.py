"""Importer for upstream knowledge-base sources.

Design:

* **Offline-first.** The importer reads a local clone of the upstream repo and
  records the exact commit SHA. No network access happens during import, so a
  sync is reproducible and never half-fetches a moving branch.
* **Licence gate.** A source can only be imported when ``redistributable`` is
  true. If someone tries to import a source without a redistribution licence,
  the importer refuses and says why. This is the technical enforcement of the
  project rule "licences and attributions are respected".
* **No overwrite of reviewed work.** Re-importing a document that a human marked
  ``reviewed`` never replaces its body. It records the new upstream hash and
  flags ``review_status = 'needs_review'`` so the change is visible.

Usage:
    python3 scripts/import_kb.py --source payloads-all-the-things --path /tmp/patt
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_models import KB_Category, KB_Document, KB_Reference, KB_Source

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

# Where each upstream section goes in our hierarchy. Anything not listed falls
# into "Referência externa" so nothing is silently dropped.
CATEGORY_MAP = {
    "SQL Injection": ("sqli", "Injeção de SQL"),
    "XSS Injection": ("xss", "Cross-Site Scripting (XSS)"),
    "Server Side Request Forgery": ("ssrf", "Server-Side Request Forgery (SSRF)"),
    "Server Side Template Injection": ("ssti", "Server-Side Template Injection (SSTI)"),
    "Command Injection": ("command-injection", "Injeção de comando"),
    "File Inclusion": ("lfi", "Inclusão de arquivos (LFI/RFI)"),
    "Directory Traversal": ("path-traversal", "Path Traversal"),
    "XXE Injection": ("xxe", "XML External Entity (XXE)"),
    "Insecure Deserialization": ("deserialization", "Desserialização insegura"),
    "Cross-Site Request Forgery": ("csrf", "Cross-Site Request Forgery (CSRF)"),
    "JSON Web Token": ("jwt", "Ataques a JWT"),
    "GraphQL Injection": ("graphql", "GraphQL"),
    "NoSQL Injection": ("nosql", "NoSQL Injection"),
    "LDAP Injection": ("ldap", "LDAP Injection"),
    "XPATH Injection": ("xpath", "XPath Injection"),
    "SSTI": ("ssti", "Server-Side Template Injection (SSTI)"),
    "Server Side Include Injection": ("ssi", "SSI Injection"),
    "CRLF Injection": ("crlf", "CRLF Injection"),
    "Open Redirect": ("open-redirect", "Open Redirect"),
    "CORS Misconfiguration": ("cors", "Configuração incorreta de CORS"),
    "Clickjacking": ("clickjacking", "Clickjacking"),
    "Prototype Pollution": ("prototype-pollution", "Prototype Pollution"),
    "Race Condition": ("race-conditions", "Race Conditions"),
    "Request Smuggling": ("request-smuggling", "HTTP Request Smuggling"),
    "Web Cache Deception": ("cache-deception", "Cache Deception"),
    "Upload Insecure Files": ("file-upload", "Upload de arquivos"),
    "Insecure Direct Object References": ("idor", "IDOR"),
    "Mass Assignment": ("mass-assignment", "Mass Assignment"),
    "Business Logic Errors": ("business-logic", "Falhas de lógica de negócio"),
    "API Key Leaks": ("secrets-exposure", "Exposição de segredos"),
    "Insecure Source Code Management": ("git-exposure", "Vazamento de código-fonte"),
    "Prompt Injection": ("prompt-injection", "Prompt Injection"),
    "Web Sockets": ("websockets", "WebSockets"),
    "Virtual Hosts": ("host-header", "Host Header / Virtual Hosts"),
    "DOM Clobbering": ("dom-clobbering", "DOM Clobbering"),
    "OAuth Misconfiguration": ("oauth", "OAuth"),
    "SAML Injection": ("saml", "SAML Injection"),
    "Type Juggling": ("type-juggling", "Type Juggling"),
    "Tabnabbing": ("tabnabbing", "Tabnabbing"),
    "XS-Leak": ("xs-leak", "XS-Leak"),
    "Zip Slip": ("zip-slip", "Zip Slip"),
    "Denial of Service": ("dos", "Negação de serviço"),
    "Insecure Randomness": ("insecure-randomness", "Aleatoriedade insegura"),
    "Dependency Confusion": ("dependency-confusion", "Dependency Confusion"),
    "Hidden Parameters": ("hidden-params", "Parâmetros ocultos"),
    "HTTP Parameter Pollution": ("hpp", "HTTP Parameter Pollution"),
    "ORM Leak": ("orm-leak", "ORM Leak"),
    "Regular Expression": ("redos", "ReDoS"),
    "XSLT Injection": ("xslt", "XSLT Injection"),
    "External Variable Modification": ("xslt", "XSLT Injection"),
    "Client Side Path Traversal": ("csp", "Client-Side Security"),
    "CSS Injection": ("css-injection", "CSS Injection"),
    "CSV Injection": ("csv-injection", "CSV Injection"),
    "Encoding Transformations": ("encoding", "Transformações de encoding"),
    "LaTeX Injection": ("latex-injection", "LaTeX Injection"),
    "Java RMI": ("java-rmi", "Java RMI"),
    "Google Web Toolkit": ("gwt", "Google Web Toolkit"),
    "Headless Browser": ("headless-browser", "Headless Browser"),
    "Insecure Management Interface": ("management-interface", "Interface administrativa insegura"),
    "Reverse Proxy Misconfigurations": ("reverse-proxy", "Reverse Proxy"),
    "CVE Exploits": ("cve-exploits", "Exploits de CVE"),
}

# Imported-only categories (not in the canonical tree) need an explicit group,
# otherwise every one of them would show up under "Web Application Security".
CATEGORY_GROUPS = {
    "methodology-and-resources": "web",
    "cve-exploits": "advanced",
    "xslt": "server",
    "insecure-randomness": "advanced",
    "brute-force-rate-limit": "auth",
    "crlf": "web",
    "css-injection": "client",
    "csv-injection": "files",
    "dns-rebinding": "server",
    "dependency-confusion": "advanced",
    "gwt": "server",
    "hpp": "web",
    "headless-browser": "client",
    "idor": "web",
    "management-interface": "server",
    "java-rmi": "server",
    "ldap": "web",
    "latex-injection": "server",
    "dos": "server",
    "nosql": "web",
    "orm-leak": "server",
    "hidden-params": "web",
    "prompt-injection": "advanced",
    "redos": "server",
    "reverse-proxy": "server",
    "saml": "auth",
    "ssi": "server",
    "tabnabbing": "client",
    "encoding": "web",
    "type-juggling": "web",
    "xpath": "web",
    "xs-leak": "client",
    "zip-slip": "files",
}

STATUS_DRAFT = "translated"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git_commit(path: Path) -> tuple[str, str]:
    """(sha, branch) of the local clone."""
    sha = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    return sha, branch


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:110]


def split_blocks(markdown: str) -> list[dict]:
    """Split a markdown file into H2 blocks with their heading path.

    The importer keeps the original text verbatim; this only decides where the
    navigation anchors are, so the reader gets a sensible table of contents.
    """
    blocks: list[dict] = []
    current = {"level": 0, "title": "", "lines": []}
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if match:
            blocks.append(current)
            current = {"level": len(match.group(1)), "title": match.group(2).strip(), "lines": []}
        else:
            current["lines"].append(line)
    blocks.append(current)
    return [b for b in blocks if b["title"] or any(l.strip() for l in b["lines"])]


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def extract_summary(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            return stripped[1:].strip()
    return ""


def content_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def ensure_category(db: Session, slug: str, title: str, group: str = "web", order: int = 100) -> KB_Category:
    cat = db.scalar(select(KB_Category).where(KB_Category.slug == slug))
    if cat:
        # An explicit non-default group wins (imported-only categories).
        if group != "web" and cat.group_name != group:
            cat.group_name = group
        return cat
    cat = KB_Category(slug=slug, title=title, group_name=group, sort_order=order)
    db.add(cat)
    db.flush()
    return cat


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

class ImportRefused(RuntimeError):
    pass


def register_sources(db: Session) -> None:
    """Seed the source registry with the projects we know about."""
    known = [
        dict(
            slug="payloads-all-the-things",
            name="PayloadsAllTheThings",
            repo_url="https://github.com/swisskyrepo/PayloadsAllTheThings",
            license_name="MIT",
            license_url="https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/LICENSE",
            author="swisskyrepo (Swissky) e contribuidores",
            redistributable=True,
            notes="Licença MIT: redistribuição permitida preservando o copyright.",
        ),
        dict(
            slug="hacktricks",
            name="HackTricks",
            repo_url="https://github.com/HackTricks-wiki/hacktricks",
            license_name="(sem licença declarada)",
            license_url="https://github.com/HackTricks-wiki/hacktricks",
            author="Carlos Polop e contribuidores",
            redistributable=False,
            notes="Sem arquivo de licença: todos os direitos reservados. Integrado apenas como "
                  "referência externa (links), nunca como texto importado.",
        ),
        dict(
            slug="owasp-wstg",
            name="OWASP Web Security Testing Guide",
            repo_url="https://github.com/OWASP/wstg",
            license_name="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            author="OWASP Foundation",
            redistributable=False,
            notes="CC BY-SA: citado por referência; texto original não é importado.",
        ),
    ]
    for data in known:
        if db.scalar(select(KB_Source).where(KB_Source.slug == data["slug"])):
            continue
        db.add(KB_Source(**data))
    db.flush()


def import_payloads_all_the_things(db: Session, root: Path) -> dict:
    """Import every markdown file under the PATT clone, preserving attribution."""
    source = db.scalar(select(KB_Source).where(KB_Source.slug == "payloads-all-the-things"))
    if not source:
        raise ImportRefused("fonte não registrada")
    if not source.redistributable:
        raise ImportRefused(
            f"{source.name} não permite redistribuição ({source.license_name}); "
            "importe apenas como referência externa."
        )
    if not (root / "LICENSE").exists():
        raise ImportRefused(f"{root} não parece ser um clone do PayloadsAllTheThings")

    sha, branch = git_commit(root)
    source.commit_sha = sha
    source.branch = branch
    source.last_synced = _utcnow()
    source.last_checked = _utcnow()

    raw = root / "LICENSE"
    license_text = raw.read_text(encoding="utf-8")

    stats = {"created": 0, "updated": 0, "skipped_reviewed": 0, "flagged": 0, "categories": 0}
    for section in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        slug, title = CATEGORY_MAP.get(section.name, (slugify(section.name), section.name))
        category = ensure_category(db, slug, title, group=CATEGORY_GROUPS.get(slug, "web"))
        stats["categories"] += 1

        for md_file in sorted(section.rglob("*.md")):
            rel = md_file.relative_to(root).as_posix()
            text = md_file.read_text(encoding="utf-8", errors="replace")
            digest = content_hash(text)

            existing = db.scalar(
                select(KB_Document).where(
                    KB_Document.source_id == source.id, KB_Document.source_path == rel
                )
            )
            if existing:
                if existing.translation_status == "reviewed" and existing.content_hash == digest:
                    stats["skipped_reviewed"] += 1
                    continue
                if existing.content_hash == digest:
                    continue
                # Upstream changed. Never overwrite reviewed text silently.
                existing.body_original_md = text
                existing.content_hash = digest
                existing.review_status = "needs_review"
                stats["flagged"] += 1
                continue

            fragment = md_file.stem
            # Namespaced and derived from the full relative path, so slugs are
            # unique by construction (two sections can map to the same category,
            # and README.md repeats in every sub-directory).
            rel_noext = md_file.relative_to(root).with_suffix("").as_posix()
            doc_slug = "patt-" + slugify(rel_noext.replace("/", "-"))
            doc = KB_Document(
                slug=doc_slug,
                title=extract_title(text, fragment),
                summary=extract_summary(text),
                category_id=category.id,
                language="en",
                origin="imported",
                source_id=source.id,
                source_path=rel,
                source_url=f"{source.repo_url}/blob/{sha}/{rel.replace(' ', '%20')}",
                source_commit=sha,
                translation_status="untranslated",
                review_status="pending",
                body_md=text,
                body_original_md=text,
                content_hash=digest,
                word_count=len(text.split()),
                imported_at=_utcnow(),
                updated_at=_utcnow(),
            )
            db.add(doc)
            db.flush()
            db.add(
                KB_Reference(
                    document_id=doc.id,
                    title=f"PayloadsAllTheThings — {rel}",
                    organization="swisskyrepo",
                    url=doc.source_url,
                    kind="repository",
                    verified=True,
                    sort_order=10,
                )
            )
            stats["created"] += 1

    # Keep the license text next to the import so attribution survives any move.
    license_copy = Path("content/kb_licenses")
    license_copy.mkdir(parents=True, exist_ok=True)
    (license_copy / "payloads-all-the-things-LICENSE.txt").write_text(license_text, encoding="utf-8")

    db.flush()
    return stats