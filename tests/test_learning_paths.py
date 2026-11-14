"""Learning Paths tests: curriculum validation, progress, gates, recs, certificates.

Every test runs against an isolated temporary database (never the operator's
real one). The platform app is booted once per module, which also runs the real
lifespan seeding of KB own-docs and the four Phase-1 curricula.

Run with:  python3 -m pytest tests/test_learning_paths.py -v
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import shutil
import tempfile

import pytest

_TEST_DATA = tempfile.mkdtemp(prefix="redvault-lp-test-")
os.environ["REDVAULT_DATA"] = _TEST_DATA
os.environ.setdefault("REDVAULT_BOT", "0")
atexit.register(lambda: shutil.rmtree(_TEST_DATA, ignore_errors=True))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.lp_models import (  # noqa: E402
    LearningActivity,
    LearningActivityProgress,
    LearningCertificate,
    LearningModule,
    LearningPath,
    LearningUnit,
)
from app.lp_progress import (  # noqa: E402
    certificate_ready,
    compute_path_progress,
    load_path,
    progress_map,
)
from app.lp_schema import CurriculumError, ValidationContext, collect_stats, validate_curriculum  # noqa: E402
from app.lp_seed import build_context, duplicate_path, load_curriculum_files, validate_all  # noqa: E402
from app.lp_web import grade_activity  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

PATHS = [
    "web-application-pentesting", "api-security", "linux-security", "windows-security",
    # Phase 2
    "active-directory-pentesting", "network-pentesting",
    "wireless-security", "hardware-hacking",
    # Phase 3
    "malware-analysis", "digital-forensics", "cloud-containers", "mobile-security",
    "binary-exploitation", "reverse-engineering", "applied-crypto", "osint",
    "red-team", "iot-embedded",
]
PHASE_1 = PATHS[:4]
PHASE_2 = PATHS[4:8]
PHASE_3 = PATHS[8:]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def user_id(client) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).order_by(User.id).limit(1))
        assert user is not None
        return user.id


def _csrf(client: TestClient) -> str:
    response = client.get("/learning-paths")
    assert response.status_code == 200
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
    assert match, "CSRF meta tag missing"
    return match.group(1)


def _reset_progress() -> None:
    with SessionLocal() as db:
        for row in db.scalars(select(LearningActivityProgress)).all():
            db.delete(row)
        for cert in db.scalars(select(LearningCertificate)).all():
            db.delete(cert)
        db.commit()


def _complete_path(path_slug: str, user_id: int) -> None:
    with SessionLocal() as db:
        path = load_path(db, path_slug)
        for module in path.modules:
            for unit in module.units:
                for act in unit.activities:
                    db.add(LearningActivityProgress(user_id=user_id, activity_id=act.id, state="completed"))
        db.commit()


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

def test_all_curricula_validate(client):
    with SessionLocal() as db:
        docs, warnings = validate_all(db)
    assert {d["slug"] for d in docs} == set(PATHS)
    # Two expected warning classes only:
    #  * machine used inside a module (documented in the audit);
    #  * imported HackTricks/PATT document not present on a fresh DB.
    unexpected = [
        w for w in warnings
        if "usa a máquina" not in w and "ainda não foi importado" not in w
    ]
    assert unexpected == [], unexpected


def test_phase1_scope_is_real_content():
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_1:
        doc = docs[slug]
        stats = collect_stats(doc)
        assert stats["modules"] >= 4, slug
        assert stats["units"] >= 8, slug
        assert stats["activities"] >= 30, slug
        assert stats["gaps"] == 0, f"{slug} has declared gaps in Phase 1"
        assert stats["assessments"] >= 1, slug
        assert stats["by_kind"].get("project", 0) >= 1, slug
        assert doc["capstone"]["success_criteria"], slug
        assert doc["capstone"]["evidence"], slug


def test_phase2_scope_is_real_content():
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_2:
        doc = docs[slug]
        stats = collect_stats(doc)
        assert doc.get("phase") == 2, slug
        assert stats["modules"] >= 3, slug
        assert stats["units"] >= 8, slug
        assert stats["activities"] >= 40, slug
        assert stats["gaps"] == 0, f"{slug} has declared gaps in Phase 2"
        assert stats["assessments"] >= 1, slug
        assert stats["by_kind"].get("project", 0) >= 1, slug
        assert doc["capstone"]["success_criteria"], slug
        assert doc["capstone"]["evidence"], slug


def test_phase2_prerequisites_exist():
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_2:
        prereqs = docs[slug].get("prerequisites") or []
        assert prereqs, f"{slug} has no prerequisite: a Phase 2 track must not start from zero"
        for prereq in prereqs:
            assert prereq in docs, f"{slug} depends on unknown path {prereq}"


def test_phase2_equipment_is_always_declared():
    """Every Phase 2 activity must say what it physically needs.

    Requirement from the operator: the Hardware track must never imply that a
    task runs on their machine when it needs a scope. A blank is ambiguous, so
    Phase 2 requires an explicit class on every activity.
    """
    valid = {"software", "optional", "required", "simulated"}
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_2:
        for mod in docs[slug]["modules"]:
            for unit in mod["units"]:
                for act in unit["activities"]:
                    equipment = act.get("equipment", "")
                    assert equipment in valid, f"{slug}/{act['slug']}: equipment '{equipment}'"


def test_hardware_track_separates_software_from_equipment():
    """Hardware must be doable mostly in software, and must name what it blocks."""
    docs = {d["slug"]: d for d in load_curriculum_files()}
    hw = docs["hardware-hacking"]
    acts = [a for m in hw["modules"] for u in m["units"] for a in u["activities"]]
    software = [a for a in acts if a["equipment"] == "software"]
    needs_hw = [a for a in acts if a["equipment"] == "required"]
    assert len(software) >= len(acts) * 0.75, "Hardware track must be mostly software-only"
    assert needs_hw, "Hardware track must be explicit about what needs a device"
    # Every hardware-dependent exercise must name the device and an alternative.
    for act in needs_hw:
        body = act.get("body_md", "")
        assert "EXIGE EQUIPAMENTO" in body, act["slug"]
        assert "bloquead" in body.lower(), f"{act['slug']}: must say the task is blocked without it"


def test_phase3_scope_is_real_content():
    """Phase 3 tracks must be as real as the others: no placeholder track."""
    docs = {d["slug"]: d for d in load_curriculum_files()}
    assert len(PHASE_3) == 10
    for slug in PHASE_3:
        doc = docs[slug]
        stats = collect_stats(doc)
        assert doc.get("phase") == 3, slug
        assert stats["modules"] >= 4, slug
        assert stats["units"] >= 6, slug
        assert stats["activities"] >= 20, slug
        assert stats["gaps"] == 0, f"{slug} declares gaps"
        assert stats["assessments"] >= 1, slug
        assert stats["by_kind"].get("project", 0) >= 1, slug
        assert doc["capstone"]["success_criteria"], slug
        assert doc["capstone"]["evidence"], slug


def test_phase3_prerequisites_exist():
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_3:
        for prereq in docs[slug].get("prerequisites") or []:
            assert prereq in docs, f"{slug} depends on unknown path {prereq}"


def test_phase3_does_not_invent_labs():
    """The platform has no lab for these areas; a lab slug must not be invented.

    Whatever ``challenge_slug`` appears must resolve to a real platform target,
    and Phase 3 tracks may not lean on them for their core practice.
    """
    docs = {d["slug"]: d for d in load_curriculum_files()}
    real = set()
    with SessionLocal() as db:
        real = {c for (c,) in db.execute(__import__("sqlalchemy").text("select slug from challenges"))}
    for slug in PHASE_3:
        acts = [a for m in docs[slug]["modules"] for u in m["units"] for a in u["activities"]]
        labs = [a for a in acts if a.get("challenge_slug")]
        assert len(labs) <= 2, f"{slug} leans on platform labs that do not exist for the area"
        for lab in labs:
            assert lab["challenge_slug"] in real, lab["challenge_slug"]


def test_phase3_equipment_is_always_declared():
    """IoT and every Phase 3 track must say what each activity physically needs."""
    valid = {"software", "optional", "required", "simulated"}
    docs = {d["slug"]: d for d in load_curriculum_files()}
    for slug in PHASE_3:
        for mod in docs[slug]["modules"]:
            for unit in mod["units"]:
                for act in unit["activities"]:
                    equipment = act.get("equipment", "")
                    assert equipment in valid, f"{slug}/{act['slug']}: '{equipment}'"


def test_phase3_blocked_exercises_offer_a_software_path():
    """A Phase 3 activity that needs a device must accept a software delivery.

    This is the operator's rule taken to its conclusion: not presuming
    equipment means every blocked exercise still has a way to be completed.
    """
    docs = {d["slug"]: d for d in load_curriculum_files()}
    checked = 0
    for slug in PHASE_3:
        for mod in docs[slug]["modules"]:
            for unit in mod["units"]:
                for act in unit["activities"]:
                    if act.get("equipment") != "required":
                        continue
                    checked += 1
                    body = act.get("body_md", "")
                    assert "EXIGE EQUIPAMENTO" in body, act["slug"]
                    lowered = body.lower()
                    assert any(w in lowered for w in ("alternativa", "plano", "sem equipamento")), (
                        f"{act['slug']}: blocked task must say what can be done without the device"
                    )
    assert checked >= 1


def test_equipment_field_is_seeded_and_rendered(client):
    with SessionLocal() as db:
        hw = load_path(db, "hardware-hacking")
        values = {a.equipment for m in hw.modules for u in m.units for a in u.activities}
        assert values <= {"software", "simulated", "required", "optional"}
        assert "required" in values
    response = client.get("/learning-paths/hardware-hacking")
    assert response.status_code == 200
    assert "SOMENTE SOFTWARE" in response.text
    assert "EXIGE EQUIPAMENTO" in response.text


def test_missing_slug_aborts_validation(client):
    docs = load_curriculum_files()
    with SessionLocal() as db:
        ctx = build_context(db)
        ctx.path_slugs = {d["slug"] for d in docs}
        broken = {
            "slug": "broken-test", "title": "Broken", "summary": "x",
            "entry_level": "a", "exit_level": "b", "estimated_hours": 1,
            "modules": [{
                "slug": "m", "title": "M", "objective": "o",
                "units": [{
                    "slug": "u", "title": "U",
                    "activities": [{"slug": "a", "kind": "lab", "title": "A", "challenge_slug": "nao-existe"}],
                }],
            }],
            "capstone": {"objective": "o", "success_criteria": ["c"], "evidence": ["e"], "grading_md": "g"},
        }
        with pytest.raises(CurriculumError, match="challenge_slug 'nao-existe'"):
            validate_curriculum(broken, ctx, "test")


def test_declared_gap_is_allowed():
    ctx = ValidationContext(kb_slugs=set(), academy_slugs=set(), challenge_slugs=set(),
                            challenge_kind={}, challenge_category={}, challenge_tags={}, source_names=set())
    wrapper = {
        "slug": "gap-test", "title": "Gap", "summary": "x", "entry_level": "a",
        "exit_level": "b", "estimated_hours": 1,
        "modules": [{"slug": "m", "title": "M", "objective": "o", "units": [{
            "slug": "u", "title": "U",
            "activities": [
                {"slug": "a", "kind": "theory", "title": "A", "gap": "SDR sem documento"},
                {"slug": "p", "kind": "project", "title": "Projeto", "body_md": "Entregar evidência."},
            ],
        }]}],
        "capstone": {"objective": "o", "success_criteria": ["c"], "evidence": ["e"], "grading_md": "g"},
    }
    validate_curriculum(wrapper, ctx, "test")


def test_seeded_db_matches_curriculum(client):
    with SessionLocal() as db:
        paths = db.scalars(select(LearningPath).order_by(LearningPath.priority)).all()
        assert {p.slug for p in paths} == set(PATHS)
        # Priority must be a strict ordering, so the UI has a stable sequence.
        priorities = [p.priority for p in paths]
        assert len(set(priorities)) == len(priorities), priorities
        for path in paths:
            assert path.modules, path.slug
            for module in path.modules:
                assert module.units, module.slug
                for unit in module.units:
                    assert unit.activities, unit.slug


def test_no_duplicate_activity_slugs_within_path(client):
    with SessionLocal() as db:
        for slug in PATHS:
            path = load_path(db, slug)
            seen = [a.slug for m in path.modules for u in m.units for a in u.activities]
            assert len(seen) == len(set(seen)), slug


# ---------------------------------------------------------------------------
# Progress and gates
# ---------------------------------------------------------------------------

def test_progress_starts_empty(client, user_id):
    _reset_progress()
    with SessionLocal() as db:
        path = load_path(db, "web-application-pentesting")
        pp = compute_path_progress(path, progress_map(db, user_id, path))
    assert pp.completed == 0 and pp.percent == 0
    assert not pp.started
    assert not pp.completed_all


def test_opening_a_page_does_not_complete_anything(client, user_id):
    _reset_progress()
    for slug in PATHS:
        response = client.get(f"/learning-paths/{slug}")
        assert response.status_code == 200
    with SessionLocal() as db:
        rows = db.scalars(select(LearningActivityProgress)).all()
    assert rows == [], "GET must never create progress rows"


def test_state_endpoint_persists(client, user_id):
    _reset_progress()
    token = _csrf(client)
    with SessionLocal() as db:
        act = db.scalar(select(LearningActivity).where(LearningActivity.kind == "theory"))
        act_id = act.id
    response = client.post(
        f"/learning-paths/activity/{act_id}/state",
        data={"_csrf": token, "state": "completed"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    with SessionLocal() as db:
        row = db.scalar(select(LearningActivityProgress).where(LearningActivityProgress.activity_id == act_id))
        assert row.state == "completed"
        assert row.completed_at is not None


def test_module_gate_blocks_until_predecessor_complete(client, user_id):
    _reset_progress()
    with SessionLocal() as db:
        path = load_path(db, "web-application-pentesting")
        assert path.modules[1].requires_module == path.modules[0].slug
        first = path.modules[0]
        # complete only the first unit of module 0
        for act in first.units[0].activities:
            db.add(LearningActivityProgress(user_id=user_id, activity_id=act.id, state="completed"))
        db.commit()
        pp = compute_path_progress(path, progress_map(db, user_id, path))
    from app.lp_progress import module_gate_met

    assert not module_gate_met(path, path.modules[1], pp)
    assert pp.module_state[path.modules[0].slug]["complete"] is False


def test_complete_path_requires_every_required_activity(client, user_id):
    _reset_progress()
    with SessionLocal() as db:
        path = load_path(db, "linux-security")
        acts = [a for m in path.modules for u in m.units for a in u.activities]
        # complete all but the last required activity
        for act in acts[:-1]:
            db.add(LearningActivityProgress(user_id=user_id, activity_id=act.id, state="completed"))
        db.commit()
        pp = compute_path_progress(path, progress_map(db, user_id, path))
        assert not pp.completed_all
        assert not certificate_ready(path, pp)

        db.add(LearningActivityProgress(user_id=user_id, activity_id=acts[-1].id, state="completed"))
        db.commit()
        pp = compute_path_progress(path, progress_map(db, user_id, path))
        assert pp.completed_all
        assert certificate_ready(path, pp)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def test_recommendations_respect_prerequisites(client, user_id):
    from app.lp_progress import recommend

    _reset_progress()
    with SessionLocal() as db:
        recs = recommend(db, user_id, limit=40)
    kinds = {r.kind for r in recs}
    assert "prerequisite" in kinds, "API path must be reported as locked"
    # The first suggestion must come from an unlocked path with no prerequisites.
    nexts = [r for r in recs if r.kind in {"next_activity", "lab"}]
    assert nexts
    assert nexts[0].path_slug in {"web-application-pentesting", "linux-security"}
    assert all(r.path_slug != "api-security" for r in nexts)


def test_recommendations_surface_review_items_first(client, user_id):
    from app.lp_progress import recommend

    _reset_progress()
    with SessionLocal() as db:
        act = db.scalar(select(LearningActivity).where(LearningActivity.kind == "theory"))
        db.add(LearningActivityProgress(user_id=user_id, activity_id=act.id, state="review"))
        db.commit()
        recs = recommend(db, user_id, limit=5)
    assert recs[0].kind == "review"
    assert recs[0].title == act.title


# ---------------------------------------------------------------------------
# Assessment grading
# ---------------------------------------------------------------------------

def test_grading_accepts_and_rejects(client):
    with SessionLocal() as db:
        act = db.scalar(
            select(LearningActivity).where(
                LearningActivity.slug == "m0-u2-assess"
            )
        )
        assert act is not None
        percent, results = grade_activity(act, {"q1": "servidor", "q2": "bundle", "q3": "não"})
        assert percent == 100 and all(r["ok"] for r in results)
        percent, results = grade_activity(act, {"q1": "cliente", "q2": "nada", "q3": "sim"})
        assert percent == 0 and not any(r["ok"] for r in results)


def test_grading_endpoint_marks_completion(client, user_id):
    _reset_progress()
    token = _csrf(client)
    with SessionLocal() as db:
        act = db.scalar(select(LearningActivity).where(LearningActivity.slug == "m0-u2-assess"))
        act_id = act.id
    response = client.post(
        f"/learning-paths/activity/{act_id}/grade",
        data={"_csrf": token, "q_q1": "servidor", "q_q2": "bundle", "q_q3": "nao"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Aprovado" in response.text
    with SessionLocal() as db:
        row = db.scalar(select(LearningActivityProgress).where(LearningActivityProgress.activity_id == act_id))
        assert row.state == "completed" and row.score == 100


def test_grading_endpoint_rejects_below_threshold(client, user_id):
    _reset_progress()
    token = _csrf(client)
    with SessionLocal() as db:
        act = db.scalar(select(LearningActivity).where(LearningActivity.slug == "m0-u2-assess"))
        act_id = act.id
    client.post(
        f"/learning-paths/activity/{act_id}/grade",
        data={"_csrf": token, "q_q1": "cliente", "q_q2": "x", "q_q3": "sim"},
        follow_redirects=True,
    )
    with SessionLocal() as db:
        row = db.scalar(select(LearningActivityProgress).where(LearningActivityProgress.activity_id == act_id))
        assert row.state != "completed"


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

def test_certificate_refused_when_incomplete(client, user_id):
    _reset_progress()
    token = _csrf(client)
    response = client.post(
        "/learning-paths/linux-security/certificate",
        data={"_csrf": token},
        follow_redirects=True,
    )
    assert "Conclusão não atingida" in response.text
    with SessionLocal() as db:
        assert db.scalars(select(LearningCertificate)).all() == []


def test_certificate_issued_and_states_private_record(client, user_id):
    _reset_progress()
    _complete_path("linux-security", user_id)
    token = _csrf(client)
    response = client.post(
        "/learning-paths/linux-security/certificate",
        data={"_csrf": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "registro privado de estudos" in response.text.lower()
    assert "não é uma certificação profissional" in response.text.lower()
    with SessionLocal() as db:
        cert = db.scalar(select(LearningCertificate))
        assert cert is not None and cert.serial.startswith("RV-LP-")
        assert cert.activities_completed > 0


def test_certificate_is_idempotent(client, user_id):
    _reset_progress()
    _complete_path("linux-security", user_id)
    token = _csrf(client)
    for _ in range(2):
        client.post("/learning-paths/linux-security/certificate", data={"_csrf": token}, follow_redirects=True)
    with SessionLocal() as db:
        assert len(db.scalars(select(LearningCertificate)).all()) == 1


# ---------------------------------------------------------------------------
# Custom paths
# ---------------------------------------------------------------------------

def test_duplicate_path_copies_tree_and_is_custom(client, user_id):
    slug = "custom-dup-test"
    with SessionLocal() as db:
        existing = db.scalar(select(LearningPath).where(LearningPath.slug == slug))
        if existing:
            db.delete(existing)
            db.commit()
        copy = duplicate_path(db, "linux-security", slug, "Cópia de teste")
        assert copy.is_custom
        assert len(copy.modules) == 5
        assert copy.capstone is not None
        acts = [a for m in copy.modules for u in m.units for a in u.activities]
        assert len(acts) > 50
        # cleaning up keeps the isolated DB tidy for the next assertion
        db.delete(copy)
        db.commit()
        assert db.scalar(select(LearningPath).where(LearningPath.slug == slug)) is None


def test_duplicate_rejects_existing_slug(client):
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            duplicate_path(db, "linux-security", "api-security", "x")


def test_custom_creation_endpoint(client, user_id):
    token = _csrf(client)
    slug = "custom-endpoint-test"
    with SessionLocal() as db:
        existing = db.scalar(select(LearningPath).where(LearningPath.slug == slug))
        if existing:
            db.delete(existing)
            db.commit()
    response = client.post(
        "/learning-paths/custom",
        data={"_csrf": token, "title": "Trilha do operador", "slug": slug, "goal": "Testar o motor."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        path = db.scalar(select(LearningPath).where(LearningPath.slug == slug))
        assert path is not None and path.is_custom
        assert path.status == "draft"
        assert path.modules and path.modules[0].units
        db.delete(path)
        db.commit()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def test_pages_render(client):
    for url in ["/learning-paths", "/learning-paths/recommendations"] + [
        f"/learning-paths/{slug}" for slug in PATHS
    ]:
        response = client.get(url)
        assert response.status_code == 200, url
        assert "Internal Server Error" not in response.text, url


def test_own_kb_documents_are_linked_and_translated(client):
    from app.kb_models import KB_Document

    with SessionLocal() as db:
        own = db.scalars(select(KB_Document).where(KB_Document.origin == "own")).all()
        slugs = {d.slug for d in own}
        assert {
            "own-gtfobins-metodologia", "own-lolbas-metodologia", "own-ntfs-para-pentest",
            "own-bola-autorizacao-objeto", "own-oidc-openid-connect",
        } <= slugs
        for doc in own:
            assert doc.language == "pt-BR"
            assert doc.word_count > 500, doc.slug
        # every own doc referenced by a curriculum must resolve
        for slug in slugs:
            assert client.get(f"/kb/d/{slug}").status_code == 200


# ---------------------------------------------------------------------------
# Language: pt-BR everywhere except technical terms
# ---------------------------------------------------------------------------

# English function words. A technical term never needs them; a sentence does.
# Deliberately narrow: short words that are also Portuguese ("use", "open",
# "path", "unit", "all") only count when combined with a real English marker.
_ENGLISH_PROSE = re.compile(
    r"\b(with|without|your|must|should|requires|optional|exercise|report|"
    r"evidence|write|recommend|recommendation|favorite|difficulty|results|"
    r"filters|search|the and|and the|the with)\b",
    re.I,
)

# Terms that legitimately stay in English inside a pt-BR sentence.
_ALLOWED_EN = {
    "living off the land",   # name of a technique (LOLBAS)
    "pass the hash", "pass the key", "pass the ticket",  # attack names
    "read-only",
}

# English sentences that are *labels*, not terms. These must never appear.
_FORBIDDEN_LABELS = re.compile(
    r"\b(next activity|next module|previous|go back|start here|mark as (done|complete)|"
    r"learn more|view details|continue learning|no results|loading)\b",
    re.I,
)


def _strings(value, where=""):
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, f"{where}.{k}" if where else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f"{where}[{i}]")


def test_curriculum_text_is_portuguese():
    """Titles, objectives and criteria must be pt-BR; only terms stay English.

    This is a guard, not a style opinion: it fails as soon as a generator
    ships an untranslated label, which is easy to do when a track is written
    quickly.
    """
    offenders = []
    for doc in load_curriculum_files():
        for where, text in _strings(doc):
            # Path/field identifiers and slugs are code, not prose.
            if where in {"icon", "accent", "domain", "codename", "equipment"} or where.endswith(
                (".slug", ".kind", ".kb_slug", ".academy_slug", ".challenge_slug",
                 ".id", ".accepted", ".equipment", ".icon", ".accent", ".domain",
                 ".codename")):
                continue
            # Italics and quoted titles may cite a foreign source verbatim.
            stripped = re.sub(r"\*[^*]+\*", " ", text)
            stripped = re.sub(r"“[^”]+”|\"[^\"]+\"", " ", stripped)
            lowered = stripped.lower()
            for allowed in _ALLOWED_EN:
                lowered = lowered.replace(allowed, " ")
            for match in _ENGLISH_PROSE.finditer(lowered):
                offenders.append(f"{doc['slug']}:{where} -> '{match.group(0)}'")
    assert offenders == [], offenders[:10]


def test_ui_labels_are_portuguese(client):
    """Visible labels must be pt-BR, apart from the area's own name."""
    pages = ["/learning-paths", "/learning-paths/recommendations"] + [
        f"/learning-paths/{slug}" for slug in PATHS
    ]
    offenders = []
    for url in pages:
        html = client.get(url).text
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # The section name itself is a proper noun and stays as-is.
            line = line.replace("Learning Paths", " ")
            if _ENGLISH_PROSE.search(line):
                offenders.append(f"{url}: {line[:80]}")
    assert offenders == [], offenders[:10]


# Raw internal keys. They are snake_case keys of Recommendation.kind, activity
# kind or progress state; the screen must show the pt-BR label instead.
_RAW_KEYS = {
    "NEXT ACTIVE", "NEXT_ACTIVITY", "NEXT ACTIVITY",
    "REVIEW", "GAP", "PREREQUISITE",
    "NOT_STARTED", "NOT STARTED", "IN_PROGRESS", "IN PROGRESS",
    "COMPLETED", "REVIEW_RECOMMENDED", "REVIEW RECOMMENDED",
    "EXERCISES", "THEORY", "ASSESSMENT", "PROJECT", "EXTERNAL",
}


def test_no_internal_keys_leak_into_the_ui(client):
    """Internal identifiers must never reach the screen.

    Keys such as ``next_activity`` or ``not_started`` are implementation
    detail; the operator sees a pt-BR label instead. ``KIND_LABELS`` values
    (TEORIA, EXERCÍCIO, LAB, ...) are legitimate output, so this test only
    looks for raw snake_case/English keys.
    """
    leaked = []
    pages = ["/learning-paths", "/learning-paths/recommendations"] + [
        f"/learning-paths/{slug}" for slug in PATHS
    ]
    for url in pages:
        html = client.get(url).text
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        # Attributes (href, class, id) are code and are stripped above.
        for line in text.splitlines():
            if line.strip() in _RAW_KEYS:
                leaked.append(f"{url}: {line.strip()}")
    assert leaked == [], leaked[:10]


def test_recommendation_kinds_are_labelled(client):
    """A rendered recommendation shows a pt-BR kind label, never the raw key."""
    from app.lp_web import RECOMMENDATION_LABELS

    pages = ["/learning-paths", "/learning-paths/recommendations"]
    seen = set()
    for url in pages:
        html = client.get(url).text
        # Visible text only: class names such as ``lp-rec-next_activity`` are
        # CSS hooks and never reach the operator.
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        for kind in ("next_activity", "prerequisite"):
            assert f">{kind}<" not in html, f"{url} mostra a chave '{kind}'"
        for label in RECOMMENDATION_LABELS.values():
            if label in text:
                seen.add(label)
    assert seen, "nenhum rótulo de recomendação encontrado"