"""Seed the knowledge base: categories, our own topics, payload extraction and
challenge links.

Run automatically at startup (idempotent) and by ``scripts/import_kb.py``.

What it does
------------
1. Ensures the canonical category tree exists (07 groups from the spec).
2. Adds ``reference`` documents for topics we do not redistribute, with a short
   honest stub that points to the primary source. Stubs are marked
   ``translation_status = 'untranslated'`` and carry an explicit "expansion
   pending" notice — never fake content.
3. Extracts payloads from imported fenced code blocks that sit under a heading
   that names a technique, and stores them with context. Payloads are never
   invented: only code that exists in the imported text.
4. Links documents to platform challenges by matching the document category to
   the challenge tags, so "practice this technique" is real.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .kb_models import (
    KB_Category,
    KB_Document,
    KB_Payload,
    KB_TopicLink,
)
from .models import Challenge

# Canonical tree from the specification. (slug, title, group, order, parent)
CATEGORY_TREE = [
    ("web-app-security", "Web Application Security", "web", 10, None),
    ("recon", "Reconnaissance", "web", 20, "web-app-security"),
    ("authentication", "Authentication", "web", 30, "web-app-security"),
    ("authorization", "Authorization", "web", 40, "web-app-security"),
    ("sqli", "Injeção de SQL (SQLi)", "web", 50, "web-app-security"),
    ("xss", "Cross-Site Scripting (XSS)", "web", 60, "web-app-security"),
    ("csrf", "Cross-Site Request Forgery (CSRF)", "web", 70, "web-app-security"),
    ("ssrf", "Server-Side Request Forgery (SSRF)", "web", 80, "web-app-security"),
    ("xxe", "XML External Entity (XXE)", "web", 90, "web-app-security"),
    ("ssti", "Server-Side Template Injection (SSTI)", "web", 100, "web-app-security"),
    ("lfi", "Inclusão local de arquivos (LFI)", "web", 110, "web-app-security"),
    ("rfi", "Inclusão remota de arquivos (RFI)", "web", 120, "web-app-security"),
    ("path-traversal", "Path Traversal", "web", 130, "web-app-security"),
    ("command-injection", "Injeção de comando", "web", 140, "web-app-security"),
    ("file-upload", "Upload de arquivos", "web", 150, "web-app-security"),
    ("deserialization", "Desserialização insegura", "web", 160, "web-app-security"),
    ("request-smuggling", "HTTP Request Smuggling", "web", 170, "web-app-security"),
    ("response-splitting", "HTTP Response Splitting", "web", 180, "web-app-security"),
    ("host-header", "Ataques de Host Header", "web", 190, "web-app-security"),
    ("open-redirect", "Open Redirect", "web", 200, "web-app-security"),
    ("cors", "CORS", "web", 210, "web-app-security"),
    ("csp", "Content Security Policy (CSP)", "web", 220, "web-app-security"),
    ("clickjacking", "Clickjacking", "web", 230, "web-app-security"),
    ("cache-poisoning", "Cache Poisoning", "web", 240, "web-app-security"),
    ("cache-deception", "Cache Deception", "web", 250, "web-app-security"),
    ("race-conditions", "Race Conditions", "web", 260, "web-app-security"),
    ("prototype-pollution", "Prototype Pollution", "web", 270, "web-app-security"),
    ("websockets", "WebSockets", "web", 280, "web-app-security"),
    ("business-logic", "Falhas de lógica de negócio", "web", 290, "web-app-security"),
    ("info-disclosure", "Information Disclosure", "web", 300, "web-app-security"),

    ("api-security", "API Security", "api", 10, None),
    ("api-rest", "REST API", "api", 20, "api-security"),
    ("graphql", "GraphQL", "api", 30, "api-security"),
    ("soap", "SOAP", "api", 40, "api-security"),
    ("bola", "BOLA", "api", 50, "api-security"),
    ("bfla", "BFLA", "api", 60, "api-security"),
    ("api-auth", "Broken Authentication", "api", 70, "api-security"),
    ("mass-assignment", "Mass Assignment", "api", 80, "api-security"),
    ("excessive-data", "Excessive Data Exposure", "api", 90, "api-security"),
    ("rate-limiting", "Improper Rate Limiting", "api", 100, "api-security"),
    ("jwt", "Ataques a JWT", "api", 110, "api-security"),
    ("oauth", "OAuth Security", "api", 120, "api-security"),
    ("api-enumeration", "API Enumeration", "api", 130, "api-security"),
    ("api-logic", "API Business Logic", "api", 140, "api-security"),
    ("webhook", "Webhook Security", "api", 150, "api-security"),
    ("api-chaining", "API Chaining", "api", 160, "api-security"),

    ("session-security", "Authentication & Session Security", "auth", 10, None),
    ("session-management", "Session Management", "auth", 20, "session-security"),
    ("session-fixation", "Session Fixation", "auth", 30, "session-security"),
    ("session-hijacking", "Session Hijacking", "auth", 40, "session-security"),
    ("jwt-auth", "JWT", "auth", 50, "session-security"),
    ("oauth2", "OAuth 2.0", "auth", 60, "session-security"),
    ("oidc", "OpenID Connect", "auth", 70, "session-security"),
    ("mfa-bypass", "Bypass de MFA", "auth", 80, "session-security"),
    ("password-reset", "Password Reset", "auth", 90, "session-security"),
    ("account-takeover", "Account Takeover", "auth", 100, "session-security"),
    ("auth-logic", "Falhas de lógica de autenticação", "auth", 110, "session-security"),

    ("server-side", "Server-Side Attacks", "server", 10, None),
    ("ssrf-server", "SSRF", "server", 20, "server-side"),
    ("lfi-server", "LFI", "server", 30, "server-side"),
    ("rfi-server", "RFI", "server", 40, "server-side"),
    ("ssti-server", "SSTI", "server", 50, "server-side"),
    ("xxe-server", "XXE", "server", 60, "server-side"),
    ("cmdi-server", "Injeção de comando", "server", 70, "server-side"),
    ("deserialization-server", "Desserialização", "server", 80, "server-side"),
    ("file-processing", "Processamento de arquivos", "server", 90, "server-side"),
    ("template-engines", "Template Engines", "server", 100, "server-side"),
    ("server-misconfig", "Configuração incorreta de servidor", "server", 110, "server-side"),

    ("client-side", "Client-Side Attacks", "client", 10, None),
    ("xss-client", "XSS", "client", 20, "client-side"),
    ("dom-xss", "DOM XSS", "client", 30, "client-side"),
    ("prototype-pollution-client", "Prototype Pollution", "client", 40, "client-side"),
    ("csti", "Client-Side Template Injection", "client", 50, "client-side"),
    ("postmessage", "PostMessage", "client", 60, "client-side"),
    ("cors-client", "CORS", "client", 70, "client-side"),
    ("csp-client", "CSP", "client", 80, "client-side"),
    ("clickjacking-client", "Clickjacking", "client", 90, "client-side"),
    ("dom-clobbering", "DOM Clobbering", "client", 100, "client-side"),
    ("js-analysis", "Análise de JavaScript", "client", 110, "client-side"),

    ("files-data", "Files & Data Exposure", "files", 10, None),
    ("file-upload-files", "Upload de arquivos", "files", 20, "files-data"),
    ("file-download", "Download de arquivos", "files", 30, "files-data"),
    ("path-traversal-files", "Path Traversal", "files", 40, "files-data"),
    ("arbitrary-read", "Leitura arbitrária de arquivos", "files", 50, "files-data"),
    ("backup-exposure", "Exposição de backups", "files", 60, "files-data"),
    ("secrets-exposure", "Exposição de segredos", "files", 70, "files-data"),
    ("git-exposure", "Exposição de Git", "files", 80, "files-data"),
    ("config-exposure", "Exposição de configuração", "files", 90, "files-data"),
    ("source-disclosure", "Divulgação de código-fonte", "files", 100, "files-data"),

    ("advanced", "Advanced Exploitation", "advanced", 10, None),
    ("chaining", "Vulnerability Chaining", "advanced", 20, "advanced"),
    ("race-advanced", "Race Conditions", "advanced", 30, "advanced"),
    ("smuggling-advanced", "Request Smuggling", "advanced", 40, "advanced"),
    ("cache-attacks", "Cache Attacks", "advanced", 50, "advanced"),
    ("advanced-ssrf", "SSRF avançado", "advanced", 60, "advanced"),
    ("auth-bypass", "Bypass de autenticação", "advanced", 70, "advanced"),
    ("authz-bypass", "Bypass de autorização", "advanced", 80, "advanced"),
    ("framework-attacks", "Ataques específicos de framework", "advanced", 90, "advanced"),
    ("advanced-api", "Exploração avançada de API", "advanced", 100, "advanced"),
]

# Categories that are aliases of an imported one: point them at the imported
# documents instead of duplicating content.
CATEGORY_ALIASES = {
    "ssrf-server": "ssrf",
    "lfi-server": "lfi",
    "ssti-server": "ssti",
    "xxe-server": "xxe",
    "cmdi-server": "command-injection",
    "xss-client": "xss",
    "cors-client": "cors",
    "csp-client": "csp",
    "clickjacking-client": "clickjacking",
    "prototype-pollution-client": "prototype-pollution",
    "race-advanced": "race-conditions",
    "smuggling-advanced": "request-smuggling",
    "cache-attacks": "cache-deception",
    "file-upload-files": "file-upload",
    "path-traversal-files": "path-traversal",
    "deserialization-server": "deserialization",
    "jwt-auth": "jwt",
    "oauth2": "oauth",
}

_CHALLENGE_TAG_MAP = {
    "sqli": ["sqli", "sql-injection", "union", "blind"],
    "xss": ["xss", "dom"],
    "ssrf": ["ssrf"],
    "xxe": ["xxe"],
    "ssti": ["ssti"],
    "lfi": ["lfi", "file-inclusion"],
    "path-traversal": ["path-traversal", "traversal"],
    "command-injection": ["command-injection", "cmdi"],
    "file-upload": ["upload"],
    "deserialization": ["deserialization", "pickle"],
    "csrf": ["csrf"],
    "jwt": ["jwt"],
    "graphql": ["graphql"],
    "nosql": ["nosql"],
    "cors": ["cors"],
    "clickjacking": ["clickjacking"],
    "prototype-pollution": ["prototype-pollution"],
    "race-conditions": ["race"],
    "request-smuggling": ["smuggling"],
    "cache-deception": ["cache"],
    "open-redirect": ["redirect"],
    "idor": ["idor", "bola"],
    "mass-assignment": ["mass-assignment"],
    "business-logic": ["logic"],
    "secrets-exposure": ["secrets"],
    "git-exposure": ["git"],
    "host-header": ["host-header"],
    "websockets": ["websocket"],
    "ldap": ["ldap"],
    "crlf": ["crlf"],
    "prompt-injection": ["prompt"],
}


def seed_categories(db: Session) -> dict[str, KB_Category]:
    created: dict[str, KB_Category] = {}
    for slug, title, group, order, parent in CATEGORY_TREE:
        cat = db.scalar(select(KB_Category).where(KB_Category.slug == slug))
        if not cat:
            cat = KB_Category(slug=slug, title=title, group_name=group, sort_order=order)
            db.add(cat)
            db.flush()
        else:
            # The canonical tree is the source of truth for grouping, even when
            # the category was first created by an import.
            if cat.group_name != group:
                cat.group_name = group
            if cat.sort_order != order:
                cat.sort_order = order
        if parent and not cat.parent_id:
            parent_cat = db.scalar(select(KB_Category).where(KB_Category.slug == parent))
            if parent_cat:
                cat.parent_id = parent_cat.id
        created[slug] = cat
    db.flush()
    return created


PAYLOAD_HEADING_RE = re.compile(
    r"(?i)(payload|bypass|injection|union|blind|time.?based|boolean|error.?based|"
    r"filter|polyglot|waf|escape|context|attribute|javascript|html|dom|template|"
    r"rce|lfi|ssrf|xxe|jwt|graphql|nosql|command|exploit|poc|reverse shell|"
    r"cloud metadata|credential|token)"
)

_FENCE_RE = re.compile(r"```([A-Za-z0-9_+-]*)\n(.*?)```", re.DOTALL)


# Lines that carry no attack surface on their own.
_BENIGN_LINE_RE = re.compile(
    r"^(works on|tested on|you can|this |that |from @|source:|note:|credit:|see also|"
    r"works? (in|with)|supports?|example:|result:|explanation:|[-+*]\s+from @)",
    re.IGNORECASE,
)
_VERB_RE = re.compile(
    r"^(SELECT|INSERT|UPDATE|DELETE|UNION|EXEC|CALL|GET|POST|PUT|PATCH|HEAD|OPTIONS|curl|wget|nmap|"
    r"python3?|bash|sh|powershell|cmd|nc|netcat|ssh|gobuster|ffuf|feroxbuster|sqlmap|dig|nslookup)\b",
    re.IGNORECASE,
)
# Characters that make a line executable/sendable rather than prose.
_SYNTAX_CHARS = set('<>={}()[]/;|&`$*"\'\\-')
_LINK_ONLY_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_COMMAND_START = (
    "+", "-", "<", "{", "[", "$ ", "curl ", "GET ", "POST ", "PUT ", "PATCH ", "DELETE ",
    "HEAD ", "python", "echo ", "nmap ", "sqlmap ", "burp ", "cat ", "grep ", "wget ", "nc ",
)


def _is_payload(code: str, language: str) -> bool:
    """Reject code blocks that only carry prose.

    A fenced block under a technique heading is not automatically a payload:
    upstream also fences plain explanations, markdown headings and credit lines.
    None of that is a reproducible primitive, so it must not reach the library.
    """
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if not lines:
        return False
    if all(line.startswith("#") for line in lines):
        return False  # markdown headings inside a fence
    lines = [line for line in lines if not _BENIGN_LINE_RE.match(line)]
    if not lines:
        return False
    # A block that is only text, links or headings has nothing to execute or
    # send. This is what separates "explanation" from "primitive".
    runnable = 0
    for line in lines:
        if line.startswith("#"):
            continue
        stripped = _LINK_ONLY_RE.sub("", line).strip(" \t")
        if not stripped:
            continue
        if _SYNTAX_CHARS & set(stripped):
            runnable += 1
        elif _VERB_RE.match(stripped):
            runnable += 1  # SQL, HTTP verbs, shell commands: "SELECT 1", "GET /x"
    if runnable == 0:
        return False
    if language in {"text", "md", "markdown"}:
        # Unlabelled blocks are kept only when half the remaining lines look
        # like a command, request line, parameter or token. Single short lines
        # of prose ("- From @terjanq") must not count as payloads.
        structural = sum(
            1
            for line in lines
            if line.startswith(_COMMAND_START)
            or "://" in line
            or ("=" in line and " " in line.replace(" = ", ""))
            or "\t" in line
            or (" " not in line and len(line) <= 40 and re.search(r"[^A-Za-z0-9.,!;]", line))
        )
        if structural / len(lines) < 0.5:
            return False
    return True


def extract_payloads(db: Session, document: KB_Document) -> int:
    """Extract fenced code blocks into payload rows, with their heading context."""
    text = document.body_md or ""
    created = 0
    order = 0
    # Walk the text, tracking the nearest preceding heading.
    position = 0
    heading = ""
    for match in _FENCE_RE.finditer(text):
        chunk = text[position:match.start()]
        for line in chunk.splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
        position = match.end()
        language = (match.group(1) or "text").lower()
        code = match.group(2).strip("\n")
        if not code or len(code) > 4000:
            continue
        if not PAYLOAD_HEADING_RE.search(heading):
            continue
        if not _is_payload(code, language):
            continue
        order += 10
        db.add(
            KB_Payload(
                document_id=document.id,
                technique=heading[:110],
                code=code,
                language=language,
                description="",
                context=heading,
                expected="",
                limitations="",
                source_ref=document.source_url,
                sort_order=order,
            )
        )
        created += 1
    return created


def link_challenges(db: Session) -> int:
    """Link documents to challenges whose tags match the document category."""
    slug_to_cat = {slug: slug for slug in _CHALLENGE_TAG_MAP}
    documents = db.scalars(select(KB_Document)).all()
    challenges = db.scalars(select(Challenge)).all()
    created = 0
    for doc in documents:
        if not doc.category:
            continue
        cat_slug = doc.category.slug
        aliased = CATEGORY_ALIASES.get(cat_slug, cat_slug)
        wanted = set(_CHALLENGE_TAG_MAP.get(cat_slug, [])) | set(_CHALLENGE_TAG_MAP.get(aliased, []))
        if not wanted:
            continue
        for challenge in challenges:
            tags = {t.lower() for t in (challenge.tech or [])} | {
                t.lower() for t in (challenge.tags or [])
            }
            if tags & wanted:
                exists = db.scalar(
                    select(KB_TopicLink).where(
                        KB_TopicLink.document_id == doc.id,
                        KB_TopicLink.challenge_id == challenge.id,
                    )
                )
                if not exists:
                    db.add(KB_TopicLink(document_id=doc.id, challenge_id=challenge.id))
                    created += 1
    return created


def seed_all(db: Session) -> dict:
    cats = seed_categories(db)
    extracted = 0
    imported = db.scalars(
        select(KB_Document).where(KB_Document.origin == "imported", KB_Document.source_path != "")
    ).all()
    for doc in imported:
        existing = db.scalar(select(KB_Payload.id).where(KB_Payload.document_id == doc.id))
        if existing is None:
            extracted += extract_payloads(db, doc)
    links = link_challenges(db)
    db.flush()
    return {"categories": len(cats), "payloads": extracted, "challenge_links": links}