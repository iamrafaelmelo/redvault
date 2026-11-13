"""Knowledge base tests: import, licence gate, search, sync, navigation.

The importer reads a local clone of PayloadsAllTheThings. These tests build a
tiny fake repository on the fly, so they never depend on the network or on a
multi-megabyte checkout.
"""
from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_TEST_DATA = tempfile.mkdtemp(prefix="redvault-kb-test-")
os.environ["REDVAULT_DATA"] = _TEST_DATA
os.environ.setdefault("REDVAULT_BOT", "0")
atexit.register(lambda: shutil.rmtree(_TEST_DATA, ignore_errors=True))

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.kb_import import ImportRefused, import_payloads_all_the_things, register_sources  # noqa: E402
from app.kb_models import KB_Document, KB_Payload, KB_Source  # noqa: E402
from app.kb_search import rebuild, search  # noqa: E402
from app.kb_seed import seed_all  # noqa: E402
from app.kb_sync import apply_upstream_change, removed_upstream  # noqa: E402
from app.main import app  # noqa: E402

SQL_README = """# SQL Injection

> SQL injection happens when user input becomes part of a query.

## Summary

* [Authentication Bypass](#authentication-bypass)
* [UNION Based Injection](#union-based-injection)

## Authentication Bypass

Always true condition bypasses the login check.

```sql
' OR '1'='1
```

## UNION Based Injection

Append a UNION SELECT to leak other tables.

```sql
-1 UNION SELECT username, password FROM users--
```
"""

XSS_README = """# XSS Injection

> Cross-site scripting executes attacker script in a victim browser.

## HTML Context

```html
<script>alert(document.domain)</script>
```
"""


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "patt"
    (repo / "SQL Injection").mkdir(parents=True)
    (repo / "XSS Injection").mkdir(parents=True)
    (repo / "SQL Injection" / "README.md").write_text(SQL_README, encoding="utf-8")
    (repo / "SQL Injection" / "MySQL Injection.md").write_text(
        "# MySQL Injection\n\n> MySQL specifics.\n\n## Extract\n\n```sql\nSELECT @@version;\n```\n",
        encoding="utf-8",
    )
    (repo / "XSS Injection" / "README.md").write_text(XSS_README, encoding="utf-8")
    (repo / "README.md").write_text("# PayloadsAllTheThings\n", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT License\n\nCopyright (c) 2019 Swissky\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed"],
        cwd=repo, check=True,
    )
    return repo


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    return _make_repo(tmp_path_factory.mktemp("kb"))


@pytest.fixture(scope="module")
def imported(repo):
    init_db()
    with SessionLocal() as db:
        register_sources(db)
        stats = import_payloads_all_the_things(db, repo)
        seed_all(db)
        db.commit()
    ensure = rebuild()
    assert ensure >= 1
    return stats


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_import_records_provenance_and_commit(imported, repo):
    assert imported["created"] == 3
    with SessionLocal() as db:
        doc = db.query(KB_Document).filter(KB_Document.source_path == "SQL Injection/README.md").one()
        assert doc.origin == "imported"
        assert doc.language == "en"
        assert doc.translation_status == "untranslated"
        assert doc.review_status == "pending"
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        assert doc.source_commit == sha
        assert sha in doc.source_url
        source = db.get(KB_Source, doc.source_id)
        assert source.license_name == "MIT"
        assert source.redistributable is True


def test_licence_gate_refuses_non_redistributable_source(repo):
    with SessionLocal() as db:
        hacktricks = db.query(KB_Source).filter(KB_Source.slug == "hacktricks").one()
        assert hacktricks.redistributable is False
        # The importer is PATT-specific, but the registry must never mark a
        # no-licence project as redistributable.
        assert "direitos reservados" in hacktricks.notes.lower() or "sem licença" in hacktricks.notes.lower()


def test_search_finds_words_inside_documents(imported):
    hits = search("union based")
    assert hits, "FTS5 must match inside the body, not only the title"
    assert any("sql" in hit["slug"] for hit in hits)
    assert hits[0]["snip"], "results must carry a highlighted snippet"

    assert search("alert") or search("document.domain")
    assert search("zzz-not-present-anywhere") == []


def test_search_handles_malicious_query_syntax(imported):
    # A quote or FTS operator in the input must not raise or inject.
    for payload in ['"', "AND OR NOT", "a*", "((", "'; DROP TABLE kb_documents;--"]:
        assert isinstance(search(payload), list)
    with SessionLocal() as db:
        assert db.query(KB_Document).count() >= 3


def test_payloads_extracted_with_context(imported):
    with SessionLocal() as db:
        doc = db.query(KB_Document).filter(KB_Document.source_path == "SQL Injection/README.md").one()
        payloads = db.query(KB_Payload).filter(KB_Payload.document_id == doc.id).all()
        assert payloads, "fenced blocks under technique headings must become payloads"
        techniques = {p.technique for p in payloads}
        assert "Authentication Bypass" in techniques
        for payload in payloads:
            assert payload.code.strip()
            assert payload.context  # context is mandatory
        codes = " ".join(p.code for p in payloads)
        assert "' OR '1'='1" in codes
        # Original payload text is preserved verbatim.
        assert "-1 UNION SELECT username, password FROM users--" in codes


def test_sync_preserves_reviewed_translation():
    with SessionLocal() as db:
        doc = db.query(KB_Document).filter(KB_Document.source_path == "XSS Injection/README.md").one()
        doc.translation_status = "reviewed"
        doc.review_status = "ok"
        doc.body_md = "# XSS (tradução revisada por humano)"
        result = apply_upstream_change(doc, "# novíssimo upstream diferente")
        assert result == "flagged"
        assert doc.body_md == "# XSS (tradução revisada por humano)", "reviewed text must never be overwritten"
        assert doc.review_status == "needs_review"
        assert apply_upstream_change(doc, "# novíssimo upstream diferente") == "unchanged"
        db.rollback()


def test_removed_upstream_is_flagged_not_deleted():
    with SessionLocal() as db:
        doc = db.query(KB_Document).filter(KB_Document.source_path == "SQL Injection/MySQL Injection.md").one()
        before = db.query(KB_Document).count()
        affected = removed_upstream(db, doc.source_id, {"SQL Injection/MySQL Injection.md"})
        assert doc in affected
        assert doc.review_status == "upstream_removed"
        assert db.query(KB_Document).count() == before
        db.rollback()


def test_library_pages_render(client):
    for path in ("/kb", "/kb?q=union", "/kb/payloads", "/kb/sources", "/kb/c/sqli"):
        response = client.get(path)
        assert response.status_code == 200, f"{path}: {response.text[:300]}"

    doc = client.get("/kb/d/patt-sql-injection-readme")
    assert doc.status_code == 200
    assert "ORIGEM DO CONTEÚDO" in doc.text        # provenance is visible
    assert "MIT" in doc.text
    assert "NESTA PÁGINA" in doc.text              # table of contents
    assert "js-copy" in doc.text                   # payload copy buttons
    assert "PayloadsAllTheThings" in doc.text      # attribution


def test_category_hierarchy_has_groups_and_parents(client):
    page = client.get("/kb").text
    # Only groups that actually contain documents are listed: an empty group
    # is noise, not navigation.
    assert "Web Application Security" in page
    assert "Nenhum documento neste grupo" not in page
    with SessionLocal() as db:
        from app.kb_models import KB_Category

        sqli = db.query(KB_Category).filter(KB_Category.slug == "sqli").one()
        assert sqli.parent_id, "SQLi must be nested under Web Application Security"
        assert sqli.group_name == "web"


def test_empty_category_is_not_listed_but_group_page_explains_it(client):
    # "api" has canonical categories but no documents in this fixture.
    page = client.get("/kb?group=api").text
    assert "Nenhum documento neste grupo ainda" in page
    home = client.get("/kb").text
    assert "/kb?group=api" not in home


def test_imported_section_gets_its_real_group(imported):
    """Every classification is traced, not just: 'if it is web, it is web'."""
    from app.kb_import import CATEGORY_GROUPS

    with SessionLocal() as db:
        from app.kb_models import KB_Category

        # The fixture has no LDAP section, so the row must not exist yet; what
        # matters is that every imported-only slug has a declared group.
        assert db.query(KB_Category).filter(KB_Category.slug == "ldap").count() == 0
        assert CATEGORY_GROUPS["ldap"] == "web"
        assert set(CATEGORY_GROUPS.values()) <= {"web", "api", "auth", "server", "client", "files", "advanced"}


def test_toc_does_not_repeat_the_document_title():
    from app.kb_views import render_markdown

    _html, toc = render_markdown("# SQL Injection\n\n## Summary\n\ntext\n\n### Sub\n\n## Tools\n\nx")
    assert ">SQL Injection</a>" not in toc, "the H1 must not be duplicated in the sidebar"
    assert "#summary" in toc and "#tools" in toc
    # Documents without an H1 keep their TOC intact.
    _html, flat = render_markdown("## A\n\nx\n\n## B\n\ny")
    assert "#a" in flat and "#b" in flat
    assert render_markdown("plain text")[1] == ""


def test_payload_library_paginates(client):
    """Hundreds of payloads must not be rendered in one response."""
    page = client.get("/kb/payloads")
    assert page.status_code == 200
    assert page.text.count("payload-card") <= 40


def test_document_links_to_related_challenges(client, imported):
    """A category that maps to platform labs must surface them on the page."""
    from app.models import Challenge

    with SessionLocal() as db:
        has_labs = db.query(Challenge).count() > 0
    page = client.get("/kb/d/patt-sql-injection-readme").text
    if has_labs:
        assert "Labs desta técnica" in page or "/lab/" in page


def test_unknown_document_is_404(client):
    assert client.get("/kb/d/nao-existe").status_code == 404
    assert client.get("/kb/c/nao-existe").status_code == 404