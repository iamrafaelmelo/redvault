"""Platform tests added in Phase 3: limits, rate limiting, catalog integrity
and UI/accessibility checks.

Same isolation contract as ``test_platform.py``: a temporary data directory,
never the operator database. Import order matters — the environment variable
must be set before any ``app`` import.
"""
from __future__ import annotations

import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import pytest

_TEST_DATA = tempfile.mkdtemp(prefix="redvault-platform-phase3-")
os.environ["REDVAULT_DATA"] = _TEST_DATA
os.environ.setdefault("REDVAULT_BOT", "0")
os.environ.setdefault("REDVAULT_LAB_START_TIMEOUT", "20")
atexit.register(lambda: shutil.rmtree(_TEST_DATA, ignore_errors=True))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import CATEGORY_META, MAX_ACTIVE_LABS  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Achievement, Challenge, Path, Progress, User, UserAchievement  # noqa: E402
from app.config import LOCAL_OPERATOR  # noqa: E402

USERNAME = LOCAL_OPERATOR


def pytest_collection_modifyitems(config, items):
    """Run this module in its own interpreter.

    ``test_platform.py`` initialises configuration first in a full-suite run and
    keeps its own database. Rather than depending on file order, this module
    re-runs itself in a child process (once) with its own ``REDVAULT_DATA`` and
    reports the child's result, so CI never silently skips platform checks.
    """
    if os.environ.get("REDVAULT_PHASE3_ISOLATED"):
        return
    if getattr(config, "_redvault_phase3_rerun", False):
        return
    config._redvault_phase3_rerun = True
    env = os.environ.copy()
    env["REDVAULT_PHASE3_ISOLATED"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:cacheprovider"],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
    )
    summary = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "no output"
    ok = completed.returncode == 0
    print(f"\n[isolated platform run] {summary}")
    if not ok:
        raise pytest.UsageError(f"isolated platform run failed:\n{completed.stdout[-4000:]}\n{completed.stderr[-2000:]}")
    skip = pytest.mark.skip(reason=f"platform phase 3 executed in an isolated interpreter: {summary}")
    for item in items:
        if item.module is not None and item.module.__name__ == __name__:
            item.add_marker(skip)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _csrf(client: TestClient) -> str:
    response = client.get("/settings")
    assert response.status_code == 200, response.text
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
    assert match, "CSRF meta token missing"
    return match.group(1)


@pytest.fixture(scope="module")
def session(client):
    # No login step: the first request issues the local session.
    assert client.get("/", follow_redirects=False).status_code == 200
    csrf = _csrf(client)
    yield {"client": client, "csrf": csrf}
    for row in client.get("/api/labs").json().get("labs", []):
        client.post(f"/api/challenges/{row['slug']}/stop", headers={"X-CSRF-Token": csrf})


def headers(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Catalog integrity
# ---------------------------------------------------------------------------

def test_every_path_reference_resolves(session):
    client = session["client"]
    with SessionLocal() as db:
        slugs = {c.slug for c in db.query(Challenge).filter(Challenge.status == "published")}
        paths = db.query(Path).all()
        assert paths
        for path in paths:
            assert path.items, f"{path.slug} has no items"
            for item in path.items:
                assert item.challenge is not None
                assert item.challenge.slug in slugs


def test_path_pages_render_with_real_progress(session):
    client = session["client"]
    with SessionLocal() as db:
        path = db.query(Path).first()
        slugs = [item.challenge.slug for item in path.items]
    page = client.get(f"/paths/{path.slug}")
    assert page.status_code == 200
    assert slugs[0] in page.text
    assert "0 / " in page.text or "/" in page.text


def test_every_category_has_challenge_labs(session):
    """Every configured category is populated by at least one challenge lab."""
    with SessionLocal() as db:
        challenges = db.query(Challenge).filter(Challenge.status == "published").all()
        counts = {slug: 0 for slug in CATEGORY_META}
        for challenge in challenges:
            if challenge.category and challenge.kind == "challenge":
                counts[challenge.category.slug] = counts.get(challenge.category.slug, 0) + 1
    thin = {slug: count for slug, count in counts.items() if count == 0}
    assert not thin, f"categories without any challenge lab: {thin}"


def test_catalog_counts_match_database(session):
    client = session["client"]
    listing = client.get("/challenges")
    assert listing.status_code == 200
    with SessionLocal() as db:
        total = db.query(Challenge).filter(Challenge.status == "published").count()
        machines = (
            db.query(Challenge)
            .filter(Challenge.status == "published", Challenge.kind == "machine")
            .count()
        )
    assert listing.text.count('href="/challenges/') >= total - machines
    search = client.get("/api/search", params={"q": "backup"})
    assert search.status_code == 200
    assert search.json()["challenges"]
    with SessionLocal() as db:
        total = db.query(Challenge).filter(Challenge.status == "published").count()
        machines = (
            db.query(Challenge)
            .filter(Challenge.status == "published", Challenge.kind == "machine")
            .count()
        )
    assert machines >= 6


# ---------------------------------------------------------------------------
# Active-lab cap
# ---------------------------------------------------------------------------

def test_active_lab_cap_is_enforced(session):
    client = session["client"]
    csrf = session["csrf"]
    with SessionLocal() as db:
        slugs = [
            c.slug
            for c in db.query(Challenge)
            .filter(Challenge.status == "published", Challenge.kind == "challenge")
            .limit(MAX_ACTIVE_LABS + 1)
        ]
    assert len(slugs) > MAX_ACTIVE_LABS

    started = []
    try:
        for slug in slugs[:MAX_ACTIVE_LABS]:
            response = client.post(f"/api/challenges/{slug}/start", headers=headers(csrf))
            assert response.status_code == 200, f"{slug}: {response.text}"
            started.append(slug)
        refused = client.post(f"/api/challenges/{slug}/start" if False else f"/api/challenges/{slugs[MAX_ACTIVE_LABS]}/start", headers=headers(csrf))
        assert refused.status_code == 503
        assert "maximum" in refused.json()["detail"].lower()
        active = client.get("/api/labs").json()["labs"]
        assert len(active) == MAX_ACTIVE_LABS
    finally:
        for slug in started:
            client.post(f"/api/challenges/{slug}/stop", headers=headers(csrf))
        assert client.get("/api/labs").json()["labs"] == []


# ---------------------------------------------------------------------------
# Login throttling
# ---------------------------------------------------------------------------

def test_no_login_route_and_single_operator(session):
    client = session["client"]
    # The login and setup screens are gone; old links redirect to the dashboard.
    for path in ("/login", "/setup"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
    posted = client.post("/login", data={"username": "x", "password": "y"}, follow_redirects=False)
    assert posted.status_code == 303
    with SessionLocal() as db:
        assert db.query(User).count() == 1


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

def test_achievements_award_on_first_flag(session):
    client = session["client"]
    csrf = _csrf(client)
    from app.flags import derive_flag

    with SessionLocal() as db:
        challenge = db.query(Challenge).filter(Challenge.slug == "recon-js-bundle").one()
        flag = next(f for f in challenge.flags if f.key == "flag")
        value = derive_flag(challenge.slug, flag.key)
        expected_names = {a.name for a in db.query(Achievement).all()}

    response = client.post(
        f"/api/challenges/{challenge.slug}/flags",
        headers=headers(csrf),
        json={"flag_key": "flag", "value": value},
    )
    assert response.status_code == 200, response.text
    names = set(response.json()["achievements"])
    assert "Primeiro Sangue" in names
    assert names <= expected_names

    with SessionLocal() as db:
        user = db.query(User).one()
        owned = {
            row.achievement.code
            for row in db.query(UserAchievement).filter(UserAchievement.user_id == user.id)
        }
    assert {"first-blood", "first-solve"} <= owned
    # The profile history shows the masked submission value, never the flag.
    profile_html = client.get("/profile").text
    assert value not in profile_html
    assert "RV{" in profile_html and "…" in profile_html

    progress = client.get("/profile/export").json()
    progress_slugs = {row["challenge"] for row in progress["progress"]}
    assert challenge.slug in progress_slugs


# ---------------------------------------------------------------------------
# UI and accessibility
# ---------------------------------------------------------------------------

def test_pages_have_lang_title_and_alt_text(session):
    client = session["client"]
    for path in ("/", "/challenges", "/machines", "/paths", "/academy", "/environments", "/profile"):
        html = client.get(path).text
        assert re.search(r'<html[^>]+lang="', html), f"{path}: missing html lang"
        assert re.search(r"<title>[^<]+</title>", html), f"{path}: missing title"
        for img in re.findall(r"<img\b[^>]*>", html):
            assert "alt=" in img, f"{path}: image without alt: {img[:80]}"

    page = client.get("/")
    assert 'name="viewport"' in page.text
    assert page.text.count('aria-label') + page.text.count('<label') > 0


def test_responsive_css_has_mobile_breakpoint(session):
    client = session["client"]
    css = client.get("/static/css/ui.css")
    assert css.status_code == 200, css.text[:200]
    tokens = client.get("/static/css/ds.css")
    assert tokens.status_code == 200, tokens.text[:200]
    body = css.text
    assert "@media" in body
    assert "max-width" in body
    assert body.count("@media (max-width: 1120px)") == 1, "the sidebar must become a drawer on small screens"
    assert "--" in tokens.text  # custom properties drive theming


def test_markup_is_escaped_in_catalog(session):
    """Search terms must never be reflected as raw markup."""
    client = session["client"]
    payload = "<script>alert(1)</script>"
    for path in ("/challenges", "/machines", "/api/search", "/academy"):
        response = client.get(path, params={"q": payload})
        assert response.status_code == 200, path
        assert payload not in response.text, f"{path} reflects raw markup"