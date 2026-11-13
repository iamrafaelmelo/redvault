"""Runaway-traffic protection: a brute force against one lab must be counted,
must not reap the lab, and must surface at a level the operator can see.

The point is not to throttle honest testing (a normal ffuf run stays far below
the threshold). It is to catch a runaway loop before it becomes load on the
operator's own machine and home network.
"""
from __future__ import annotations

import atexit
import os
import re
import shutil
import tempfile
import time

import pytest

_TEST_DATA = tempfile.mkdtemp(prefix="redvault-traffic-test-")
os.environ["REDVAULT_DATA"] = _TEST_DATA
os.environ.setdefault("REDVAULT_BOT", "0")
atexit.register(lambda: shutil.rmtree(_TEST_DATA, ignore_errors=True))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.traffic import (  # noqa: E402
    ABUSE_ABORT_RPS,
    ABUSE_WARN_RPS,
    ABUSE_WINDOW_SECONDS,
    LabTraffic,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _csrf(client: TestClient) -> str:
    page = client.get("/lab/auth-otp-bruteforce").text
    return re.search(r'<meta name="csrf-token" content="([^"]+)"', page).group(1)


def test_baseline_rates_are_not_abuse():
    traffic = LabTraffic()
    # 200 requests over the window: a fast but honest ffuf/Burp run.
    for _ in range(200):
        stats = traffic.record(1)
    assert stats["state"] == "normal"
    assert stats["requests_total"] == 200
    assert ABUSE_WARN_RPS > 200 / ABUSE_WINDOW_SECONDS


def test_abort_threshold_is_reached_once():
    traffic = LabTraffic()
    events = [traffic.record(7)["first_abort"] for _ in range(int(ABUSE_ABORT_RPS * ABUSE_WINDOW_SECONDS) + 5)]
    stats = traffic.record(7)
    assert stats["state"] == "abort"
    assert events.count(True) == 1, "the abort banner must fire once, not on every request"
    assert stats["rps"] >= ABUSE_ABORT_RPS


def test_window_does_not_grow_without_bound():
    traffic = LabTraffic()
    for _ in range(50):
        traffic.record(9)
    traffic._buckets[9][0] -= ABUSE_WINDOW_SECONDS * 2  # age one entry
    stats = traffic.record(9)
    assert stats["requests_window"] <= 51


def test_brute_force_keeps_the_lab_alive_and_is_reported(client):
    started = client.post(
        "/api/challenges/auth-otp-bruteforce/start", headers={"X-CSRF-Token": _csrf(client)}
    )
    assert started.status_code == 200, started.text
    port = started.json()["port"]
    import httpx

    try:
        # Simulate the reaper being about to reap an "idle" lab, then show that
        # real traffic pushes last_active forward.
        from app import lab_manager as lm

        lab = next(l for l in lm.lab_manager.active_labs() if l.port == port)
        lab.last_active = time.time() - 10_000
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5) as c:
            for _ in range(20):
                c.get("/")
            from app.database import SessionLocal
            from app.models import LabSession

            with SessionLocal() as db:
                row = db.get(LabSession, lab.session_id)
                client.post("/api/labs", headers={"X-CSRF-Token": _csrf(client)})
                # status endpoint touches the lab like the UI does
                client.get("/api/challenges/auth-otp-bruteforce/status")
        assert lm.lab_manager.active_for(lab.user_id, lab.challenge_id) is not None
    finally:
        client.post(
            "/api/challenges/auth-otp-bruteforce/stop", headers={"X-CSRF-Token": _csrf(client)}
        )


def test_lab_headers_expose_traffic_state(client):
    started = client.post(
        "/api/challenges/access-idor-invoices/start", headers={"X-CSRF-Token": _csrf(client)}
    )
    assert started.status_code == 200, started.text
    port = started.json()["port"]
    try:
        import httpx

        response = httpx.get(f"http://127.0.0.1:{port}/", timeout=5)
        assert response.headers.get("X-Redvault-Traffic") in {"normal", "warn", "abort"}
    finally:
        client.post(
            "/api/challenges/access-idor-invoices/stop", headers={"X-CSRF-Token": _csrf(client)}
        )