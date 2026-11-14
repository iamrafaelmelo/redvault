#!/usr/bin/env python3
"""Shared builders used by the learning-path generator scripts.

Written as a script so the structure is checked as it is built (every slug is
read from the live platform) and the JSON stays pretty-printed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def act(slug, kind, title, *, kb="", academy="", lab="", body_md="", questions=None,
        minutes=20, required=True, gap="", equipment=""):
    out = {"slug": slug, "kind": kind, "title": title, "estimated_minutes": minutes}
    if not required:
        out["required"] = False
    if kb:
        out["kb_slug"] = kb
    if academy:
        out["academy_slug"] = academy
    if lab:
        out["challenge_slug"] = lab
    if body_md:
        out["body_md"] = body_md
    if questions:
        out["questions"] = questions
    if gap:
        out["gap"] = gap
    if equipment:
        out["equipment"] = equipment
    return out


def unit(slug, title, objective, competencies, activities, minutes=90):
    return {
        "slug": slug, "title": title, "objective": objective,
        "competencies": competencies, "estimated_minutes": minutes,
        "activities": activities,
    }


def mod(slug, title, objective, competencies, units, *, summary="", prereq="",
        completion="", minutes=180, requires=""):
    return {
        "slug": slug, "title": title, "summary": summary, "objective": objective,
        "competencies": competencies, "units": units, "prerequisites": prereq,
        "completion": completion, "estimated_minutes": minutes,
        "requires_module": requires,
    }


def default_equipment(path: dict, value: str = "software") -> dict:
    """Fill ``equipment`` on every activity that did not declare one.

    A blank is ambiguous: it could mean "runs on your machine" or "nobody
    thought about it". Phase-2 curricula declare the class explicitly so the
    UI badge is always truthful. Hardware-only activities declare their own
    value before this runs, so those are never overwritten.
    """
    for m in path["modules"]:
        for u in m["units"]:
            for a in u["activities"]:
                a.setdefault("equipment", value)
    return path


if __name__ == "__main__":
    pass
