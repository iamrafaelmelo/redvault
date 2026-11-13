"""Traffic accounting for lab processes.

A lab is a loopback (or LAN-widened) Flask process, so the only place the
platform can observe real activity is around the lab itself. Each lab is
wrapped by a small reverse proxy (``labs/_shared/serve_lab.py --serve``) that
talks to the platform's ``/internal/lab-traffic`` endpoint, which counts
requests per lab, per second and in total.

This module turns those counters into a fault that a half-asleep operator can
actually act on: "you are sending N requests/second at one lab; a bruteforce
does not need more than a few hundred, and the rest is just load on your own
machine and network".

The counters live in the platform, not in the lab, so they survive a lab reset
and cannot be forged by the intentionally vulnerable app.
"""
from __future__ import annotations

import threading
import time

# Decide what counts as abuse. These are deliberately generous: a legitimate
# ffuf/Burp Intruder run against a local lab stays far below them, and the goal
# is to catch a runaway loop, not to throttle honest testing.
ABUSE_WINDOW_SECONDS = 10
ABUSE_WARN_RPS = 300
ABUSE_ABORT_RPS = 1500


class LabTraffic:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[int, list[float]] = {}  # session_id -> recent timestamps
        self._lifetime: dict[int, int] = {}  # session_id -> total requests
        self._abort_emitted: set[int] = set()

    def record(self, session_id: int, count: int = 1) -> dict:
        """Record ``count`` requests that arrived since the last report."""
        now = time.time()
        with self._lock:
            bucket = self._buckets.setdefault(session_id, [])
            bucket.extend([now] * count)
            floor = now - ABUSE_WINDOW_SECONDS
            # Trim in place so a long brute force does not grow unbounded.
            if bucket and bucket[0] < floor:
                del bucket[: next((i for i, t in enumerate(bucket) if t >= floor), len(bucket))]
            self._lifetime[session_id] = self._lifetime.get(session_id, 0) + count
            rps = len(bucket) / ABUSE_WINDOW_SECONDS
            state = "normal"
            if rps >= ABUSE_ABORT_RPS:
                state = "abort"
            elif rps >= ABUSE_WARN_RPS:
                state = "warn"
            payload = {
                "requests_total": self._lifetime[session_id],
                "requests_window": len(bucket),
                "window_seconds": ABUSE_WINDOW_SECONDS,
                "rps": round(rps, 1),
                "state": state,
                "first_abort": False,
            }
            if state == "abort" and session_id not in self._abort_emitted:
                self._abort_emitted.add(session_id)
                payload["first_abort"] = True
        return payload

    def forget(self, session_id: int) -> None:
        with self._lock:
            self._buckets.pop(session_id, None)
            self._lifetime.pop(session_id, None)
            self._abort_emitted.discard(session_id)


lab_traffic = LabTraffic()