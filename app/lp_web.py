"""HTML routes for the Learning Paths area (``/learning-paths``).

Kept separate from ``web.py`` so the legacy ``/paths`` feature stays untouched
while the new engine is validated. Each route resolves the curriculum from the
database (seeded from ``content/learning_paths/``) and always re-reads progress
from ``lp_progress`` — nothing is cached in the session.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .deps import get_db
from .kb_models import KB_Document
from .lp_models import (
    LearningActivity,
    LearningActivityProgress,
    LearningAssessmentAttempt,
    LearningModule,
    LearningPath,
    LearningUnit,
)
from .lp_progress import (
    Recommendation,
    certificate_ready,
    compute_path_progress,
    get_certificate,
    get_or_create,
    issue_certificate,
    load_path,
    load_paths,
    module_gate_met,
    progress_map,
    recommend,
    set_state,
    update_fields,
)
from .lp_seed import duplicate_path
from .models import Challenge, User
from .security import check_csrf, current_user, local_session
from .web import flash_redirect, render

router = APIRouter()

STATE_LABELS = {
    "not_started": "NÃO INICIADO",
    "in_progress": "EM ANDAMENTO",
    "completed": "CONCLUÍDO",
    "review": "REVISÃO",
}

KIND_LABELS = {
    "theory": "TEORIA",
    "exercises": "EXERCÍCIO",
    "lab": "LAB",
    "assessment": "AVALIAÇÃO",
    "project": "PROJETO",
    "external": "EXTERNO",
}

# Filter chips on the index. The stored domain is a short key; the chip must
# read in pt-BR like every other label.
DOMAIN_LABELS = {
    "web": "WEB",
    "api": "API",
    "linux": "LINUX",
    "windows": "WINDOWS",
    "infra": "INFRA",
    "rf": "RF",
    "hardware": "HARDWARE",
    "malware": "MALWARE",
    "forensics": "FORENSE",
    "cloud": "CLOUD",
    "mobile": "MOBILE",
    "binexp": "EXPLOIT DEV",
    "reversing": "REVERSING",
    "crypto": "CRIPTO",
    "osint": "OSINT",
    "redteam": "RED TEAM",
    "iot": "IOT",
}

# How an activity says what it physically needs. Only hardware-oriented paths
# set this; everywhere else a blank means "runs on your machine".
EQUIPMENT_LABELS = {
    "software": "SOMENTE SOFTWARE",
    "optional": "EQUIPAMENTO OPCIONAL",
    "required": "EXIGE EQUIPAMENTO",
    "simulated": "EQUIPAMENTO SIMULADO",
}

# Recommendation kinds are internal keys (``next_activity``); the operator
# must never see the raw key.
RECOMMENDATION_LABELS = {
    "next_activity": "PRÓXIMA ATIVIDADE",
    "review": "REVISÃO",
    "gap": "LACUNA DE CONTEÚDO",
    "prerequisite": "PRÉ-REQUISITO",
    "lab": "LABORATÓRIO",
}

STATE_ORDER = {"in_progress": 0, "review": 1, "not_started": 2, "completed": 3}


def _user_or_redirect(request: Request, db: Session, next_url: str) -> tuple[User | None, RedirectResponse | None]:
    user = current_user(request, db)
    if user is None:
        return None, RedirectResponse(f"/login?next={next_url}", status_code=303)
    return user, None


def _activity(db: Session, activity_id: int) -> LearningActivity:
    act = db.get(LearningActivity, activity_id)
    if not act:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return act


def _path_of_activity(db: Session, act: LearningActivity) -> LearningPath:
    row = db.execute(
        select(LearningPath)
        .join(LearningModule, LearningModule.path_id == LearningPath.id)
        .join(LearningUnit, LearningUnit.module_id == LearningModule.id)
        .where(LearningUnit.id == act.unit_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    return row


def _resolve_target(db: Session, act: LearningActivity) -> dict:
    """Human-readable destination of an activity (lab, KB doc or Academy page)."""
    if act.challenge_slug:
        ch = db.scalar(select(Challenge).where(Challenge.slug == act.challenge_slug))
        if ch:
            base = "machines" if ch.kind == "machine" else "challenges"
            return {"label": ch.title, "url": f"/{base}/{ch.slug}", "kind": ch.kind}
    if act.kb_slug:
        doc = db.scalar(select(KB_Document).where(KB_Document.slug == act.kb_slug))
        if doc:
            return {"label": doc.title, "url": f"/kb/d/{doc.slug}", "kind": "kb"}
    if act.academy_slug:
        return {"label": act.academy_slug.replace("-", " ").title(), "url": f"/academy/{act.academy_slug}", "kind": "academy"}
    return {}


def _path_stats(db: Session, path: LearningPath, pmap: dict) -> dict:
    return {"progress": compute_path_progress(path, pmap)}


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

@router.get("/learning-paths", response_class=HTMLResponse)
async def learning_paths_index(
    request: Request,
    domain: str = "",
    state: str = "",
    db: Session = Depends(get_db),
):
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect

    paths = load_paths(db)
    rows = []
    for path in paths:
        pmap = progress_map(db, user.id, path)
        pp = compute_path_progress(path, pmap)
        if state == "unlocked" and not _prereqs_met(db, user.id, path):
            continue
        if state == "started" and not pp.started:
            continue
        if state == "done" and not pp.completed_all:
            continue
        if domain and path.domain != domain:
            continue
        rows.append({"path": path, "pp": pp, "unlocked": _prereqs_met(db, user.id, path)})

    unlocked = sum(1 for r in rows if r["unlocked"] and not r["pp"].completed_all)
    complete = sum(1 for r in rows if r["pp"].completed_all)
    domains = sorted({p.domain for p in paths if p.domain})

    # Recommendations only make sense when there is real progress to base them on.
    recs = recommend(db, user.id, limit=6)

    return render(
        request, db, "learning_paths.html", user, "learning_paths",
        rows=rows, domains=domains, active_domain=domain, active_state=state,
        unlocked=unlocked, complete=complete, recs=recs,
        cert_count=_certificate_count(db, user.id),
        rec_labels=RECOMMENDATION_LABELS,
        kind_labels=KIND_LABELS,
        domain_labels=DOMAIN_LABELS,
    )


def _certificate_count(db: Session, user_id: int) -> int:
    from .lp_models import LearningCertificate

    return int(db.scalar(
        select(func.count()).select_from(LearningCertificate).where(LearningCertificate.user_id == user_id)
    ) or 0)


def _prereqs_met(db: Session, user_id: int, path: LearningPath) -> bool:
    """A path is unlocked when every prerequisite path is fully complete."""
    for slug in path.prerequisites or []:
        pre = load_path(db, slug)
        if not pre:
            continue  # validation guarantees existence; a deleted path is not a lock
        pmap = progress_map(db, user_id, pre)
        if not compute_path_progress(pre, pmap).completed_all:
            return False
    return True


# ---------------------------------------------------------------------------
# Path detail
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Recommendations page
# ---------------------------------------------------------------------------

@router.get("/learning-paths/recommendations", response_class=HTMLResponse)
async def learning_path_recommendations(request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, "/learning-paths/recommendations")
    if redirect:
        return redirect
    recs = recommend(db, user.id, limit=40)
    return render(request, db, "learning_path_recommendations.html", user, "learning_paths",
                  recs=recs, rec_labels=RECOMMENDATION_LABELS)


@router.get("/learning-paths/{slug}", response_class=HTMLResponse)
async def learning_path_detail(
    request: Request,
    slug: str,
    focus: int | None = None,
    db: Session = Depends(get_db),
):
    user, redirect = _user_or_redirect(request, db, f"/learning-paths/{slug}")
    if redirect:
        return redirect

    path = load_path(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")

    pmap = progress_map(db, user.id, path)
    pp = compute_path_progress(path, pmap)

    prereqs = []
    for pre_slug in path.prerequisites or []:
        pre = load_path(db, pre_slug)
        if pre:
            pre_pp = compute_path_progress(pre, progress_map(db, user.id, pre))
            prereqs.append({"path": pre, "pp": pre_pp, "met": pre_pp.completed_all})
    unlocked = all(p["met"] for p in prereqs)

    activities_by_unit = {}
    unit_states = []
    for module in path.modules:
        gate = module_gate_met(path, module, pp)
        mstate = pp.module_state[module.slug]
        units = []
        for unit in module.units:
            acts = []
            for act in unit.activities:
                row = pmap.get(act.id)
                acts.append({
                    "act": act,
                    "state": row.state if row else "not_started",
                    "row": row,
                    "target": _resolve_target(db, act),
                    "locked": not gate,
                })
            activities_by_unit[unit.id] = acts
            done = sum(1 for a in acts if a["state"] == "completed")
            units.append({
                "unit": unit,
                "acts": acts,
                "done": done,
                "total": len(acts),
                "percent": round(done / len(acts) * 100) if acts else 0,
            })
        unit_states.append({
            "module": module,
            "units": units,
            "gate": gate,
            "state": mstate,
            "open": mstate["completed"] < mstate["total"],
        })

    cert = get_certificate(db, user.id, path.id)
    can_certify = certificate_ready(path, pp)
    focus_act = db.get(LearningActivity, focus) if focus else None

    return render(
        request, db, "learning_path_detail.html", user, "learning_paths",
        path=path, pp=pp, modules=unit_states, prereqs=prereqs, unlocked=unlocked,
        cert=cert, can_certify=can_certify, state_labels=STATE_LABELS,
        kind_labels=KIND_LABELS, focus=focus_act,
        equipment_labels=EQUIPMENT_LABELS,
    )


# ---------------------------------------------------------------------------
# Activity mutations
# ---------------------------------------------------------------------------

@router.post("/learning-paths/activity/{activity_id}/state")
async def learning_path_set_state(activity_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    state = str(form.get("state", ""))
    act = _activity(db, activity_id)
    target = _path_of_activity(db, act)
    try:
        set_state(db, user.id, act.id, state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido")
    anchor = f"#act-{act.id}"
    return flash_redirect(f"/learning-paths/{target.slug}{anchor}", f"Estado atualizado: {STATE_LABELS.get(state, state)}.")


@router.post("/learning-paths/activity/{activity_id}/notes")
async def learning_path_notes(activity_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    act = _activity(db, activity_id)
    target = _path_of_activity(db, act)
    fields = {
        "notes": str(form.get("notes", "")).strip()[:8000],
        "difficulties": str(form.get("difficulties", "")).strip()[:4000],
        "result": str(form.get("result", "")).strip()[:4000],
    }
    if "favorite" in form:
        fields["favorite"] = str(form.get("favorite")) in {"1", "on", "true"}
    if "revisit" in form:
        fields["revisit"] = str(form.get("revisit")) in {"1", "on", "true"}
    update_fields(db, user.id, act.id, **fields)
    return flash_redirect(f"/learning-paths/{target.slug}#act-{act.id}", "Anotações salvas.")


@router.post("/learning-paths/activity/{activity_id}/toggle")
async def learning_path_toggle(activity_id: int, request: Request, db: Session = Depends(get_db)):
    """Quick favourite/revisit toggle from the activity row."""
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    field = str(form.get("field", ""))
    if field not in {"favorite", "revisit"}:
        raise HTTPException(status_code=400, detail="Campo inválido")
    act = _activity(db, activity_id)
    target = _path_of_activity(db, act)
    row = get_or_create(db, user.id, act.id)
    setattr(row, field, not getattr(row, field))
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return flash_redirect(f"/learning-paths/{target.slug}#act-{act.id}", "Marcador atualizado.")


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

def _normalise(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def grade_activity(act: LearningActivity, answers: dict[str, str]) -> tuple[int, list[dict]]:
    """Grade a quiz. Returns (percent, per-question results).

    Accepted answers are compared after lowercasing and whitespace collapsing;
    a question with ``accepted`` passes when any accepted token appears as a
    whole word in the answer, which tolerates short explanatory sentences.
    """
    questions = (act.answer_key or {}).get("questions", [])
    if not questions:
        return 0, []
    results = []
    correct = 0
    for q in questions:
        raw = _normalise(str(answers.get(q["id"], "")))
        accepted = [_normalise(a) for a in (q.get("accepted") or [])]
        if not accepted and "answer" in q:
            accepted = [_normalise(str(q["answer"]))]
        ok = bool(raw) and any(
            raw == a or re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", raw)
            for a in accepted
        )
        if ok:
            correct += 1
        results.append({"id": q["id"], "prompt": q["prompt"], "ok": ok, "given": raw})
    percent = round(correct / len(questions) * 100)
    return percent, results


@router.post("/learning-paths/activity/{activity_id}/grade")
async def learning_path_grade(activity_id: int, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    act = _activity(db, activity_id)
    if act.kind != "assessment":
        raise HTTPException(status_code=400, detail="Atividade não é avaliação")
    target = _path_of_activity(db, act)

    answers = {
        key[2:]: str(value)
        for key, value in form.items()
        if key.startswith("q_")
    }
    percent, results = grade_activity(act, answers)
    passed = percent >= 70
    db.add(LearningAssessmentAttempt(
        user_id=user.id, activity_id=act.id,
        submitted={k: v[:400] for k, v in answers.items()},
        score=percent, passed=passed,
    ))
    row = get_or_create(db, user.id, act.id)
    row.score = percent
    row.state = "completed" if passed else ("in_progress" if row.state == "not_started" else row.state)
    if passed and not row.completed_at:
        row.completed_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    detail = ", ".join(f"{r['id']}:{'ok' if r['ok'] else 'erro'}" for r in results)
    kind = "ok" if passed else "warn"
    return flash_redirect(
        f"/learning-paths/{target.slug}#act-{act.id}",
        f"Avaliação: {percent}% ({detail}). {'Aprovado.' if passed else 'Abaixo de 70% — revise os itens errados.'}",
        kind=kind,
    )


# ---------------------------------------------------------------------------
# Capstone submission
# ---------------------------------------------------------------------------

@router.post("/learning-paths/{slug}/capstone")
async def learning_path_capstone(slug: str, request: Request, db: Session = Depends(get_db)):
    """Record capstone evidence and completion.

    The platform cannot verify a written report automatically, so the operator
    marks the capstone as delivered together with the evidence links. Completion
    then requires the configured checks (flags of the machine, when defined).
    """
    user, redirect = _user_or_redirect(request, db, f"/learning-paths/{slug}")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    path = load_path(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    evidence = str(form.get("evidence", "")).strip()[:4000]
    if len(evidence) < 40:
        return flash_redirect(
            f"/learning-paths/{slug}#capstone",
            "Descreva a evidência entregue (mínimo 40 caracteres) antes de marcar o capstone.",
            kind="warn",
        )
    project = next(
        (a for m in path.modules for u in m.units for a in u.activities if a.kind == "project"),
        None,
    )
    if not project:
        return flash_redirect(f"/learning-paths/{slug}#capstone", "Esta trilha não define atividade de projeto.", kind="warn")
    update_fields(db, user.id, project.id, notes=evidence)
    row = get_or_create(db, user.id, project.id)
    row.state = "completed"
    row.completed_at = row.completed_at or datetime.now(timezone.utc)
    row.result = "Capstone entregue"
    db.commit()
    return flash_redirect(f"/learning-paths/{slug}#capstone", "Capstone registrado. Verifique os critérios de conclusão.")


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

@router.post("/learning-paths/{slug}/certificate")
async def learning_path_certificate(slug: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, f"/learning-paths/{slug}")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    path = load_path(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    pp = compute_path_progress(path, progress_map(db, user.id, path))
    if not certificate_ready(path, pp):
        missing = pp.required_total - pp.required_done
        return flash_redirect(
            f"/learning-paths/{slug}",
            f"Conclusão não atingida: {missing} atividade(s) obrigatória(s) pendente(s).",
            kind="warn",
        )
    cert = issue_certificate(db, user.id, path, pp)
    return flash_redirect(f"/learning-paths/{slug}/certificate", f"Certificado {cert.serial} emitido.")


@router.get("/learning-paths/{slug}/certificate", response_class=HTMLResponse)
async def learning_path_certificate_view(slug: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, f"/learning-paths/{slug}")
    if redirect:
        return redirect
    path = load_path(db, slug)
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    cert = get_certificate(db, user.id, path.id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado não emitido")
    return render(request, db, "learning_path_certificate.html", user, "learning_paths",
                  path=path, cert=cert, user_obj=user)


# ---------------------------------------------------------------------------
# Custom paths
# ---------------------------------------------------------------------------

@router.post("/learning-paths/custom")
async def learning_path_create(request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, "/learning-paths")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    title = str(form.get("title", "")).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", str(form.get("slug", "")).strip().lower()).strip("-")
    source = str(form.get("source_slug", "")).strip()
    goal = str(form.get("goal", "")).strip()[:2000]
    if not title or not slug:
        return flash_redirect("/learning-paths", "Título e slug são obrigatórios.", kind="warn")
    if db.scalar(select(LearningPath).where(LearningPath.slug == slug)):
        return flash_redirect("/learning-paths", f"Já existe uma trilha com o slug '{slug}'.", kind="warn")
    try:
        if source:
            path = duplicate_path(db, source, slug, title)
        else:
            from .lp_models import LearningModule, LearningUnit
            from .lp_models import LearningCapstone

            path = LearningPath(
                slug=slug, title=title, codename="CUSTOM", domain="custom",
                summary=goal or "Trilha personalizada.", description=goal,
                entry_level=str(form.get("entry_level", "")).strip() or "definido pelo operador",
                exit_level=str(form.get("exit_level", "")).strip() or "definido pelo operador",
                estimated_hours=int(form.get("estimated_hours") or 10),
                priority=500, phase=0, icon="route", accent="violet",
                prerequisites=[], competencies=[], tools=[], equipment="definido pelo operador",
                is_custom=True, status="draft",
            )
            db.add(path)
            db.flush()
            module = LearningModule(
                path_id=path.id, slug="inicio", title="Início", position=1,
                objective="Definir o caminho desta trilha personalizada.",
            )
            db.add(module)
            db.flush()
            unit = LearningUnit(module_id=module.id, slug="objetivos", title="Objetivos", position=1,
                                objective="Registrar o que deve ser estudado e como será verificado.")
            db.add(unit)
            db.flush()
            db.add(LearningActivity(
                unit_id=unit.id, slug="objetivo", kind="exercises", position=1,
                title="Registrar objetivos da trilha", body_md=goal or "Descreva o objetivo desta trilha.",
            ))
            db.add(LearningCapstone(
                path_id=path.id, objective="Projeto final definido pelo operador.",
                success_criteria=["Critério definido pelo operador"],
                evidence=["Evidência definida pelo operador"],
                grading_md="Avaliação definida pelo operador.",
            ))
            db.commit()
    except ValueError as exc:
        db.rollback()
        return flash_redirect("/learning-paths", f"Erro ao criar trilha: {exc}", kind="warn")
    if path.status == "draft":
        return flash_redirect(f"/learning-paths/{path.slug}", "Trilha personalizada criada. Adicione as atividades pela edição do currículo.")
    return flash_redirect(f"/learning-paths/{path.slug}", f"Trilha duplicada de '{source}'. Edite o currículo para personalizar.")


@router.post("/learning-paths/{slug}/archive")
async def learning_path_archive(slug: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = _user_or_redirect(request, db, f"/learning-paths/{slug}")
    if redirect:
        return redirect
    form = await request.form()
    check_csrf(request, str(form.get("_csrf", "")))
    path = db.scalar(select(LearningPath).where(LearningPath.slug == slug))
    if not path:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    if not path.is_custom:
        return flash_redirect(f"/learning-paths/{slug}", "Apenas trilhas personalizadas podem ser arquivadas.", kind="warn")
    path.status = "archived"
    db.commit()
    return flash_redirect("/learning-paths", "Trilha personalizada arquivada.")