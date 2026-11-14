"""Curriculum schema and validation for Learning Paths.

The curriculum lives as JSON under ``content/learning_paths/``. Validation is
strict on purpose: a slug that does not exist in the platform is a hard error,
because the acceptance criteria forbid associating an inexistent lab, document
or challenge. Missing *content* is allowed only when declared explicitly as a
``gap`` with the topic that has to be written.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VALID_KINDS = {"theory", "exercises", "lab", "assessment", "project", "external"}

#: Physical requirement of an activity. Empty means the path's own statement
#: applies; hardware curricula set it on every activity so that a task that
#: needs a scope is never mistaken for one that runs on the operator's machine.
VALID_EQUIPMENT = {
    "software",     # runs entirely on the operator's existing machine
    "optional",     # best with a device, but has a software-only equivalent
    "required",     # cannot be completed without the named physical device
    "simulated",    # needs a device that is emulated in software
}


class CurriculumError(ValueError):
    """Raised when a curriculum file references something that does not exist."""


@dataclass
class ValidationContext:
    """Everything a curriculum is allowed to reference."""

    kb_slugs: set[str]
    academy_slugs: set[str]
    challenge_slugs: set[str]
    challenge_kind: dict[str, str]          # slug -> challenge|machine
    challenge_category: dict[str, str]      # slug -> category slug
    challenge_tags: dict[str, set[str]]     # slug -> tags
    source_names: set[str] = field(default_factory=set)
    #: False when no imported KB content is present (fresh install before
    #: ``scripts/import_kb.py``). References to imported documents then become a
    #: warning instead of a fatal error, because the document is not missing —
    #: it was simply never imported on this machine.
    kb_imported: bool = False
    path_slugs: set[str] = field(default_factory=set)
    seen_paths: set[str] = field(default_factory=set)


def _require_keys(obj: dict, keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if k not in obj or obj[k] in (None, "")]
    if missing:
        raise CurriculumError(f"{where}: campos obrigatórios ausentes: {', '.join(missing)}")


def validate_activity(act: dict, where: str, ctx: ValidationContext) -> list[str]:
    """Validate one activity. Returns a list of non-fatal warnings."""
    warnings: list[str] = []
    _require_keys(act, ("slug", "kind", "title"), where)
    _check_code_spans(where, "title", act["title"])
    kind = act["kind"]
    if kind not in VALID_KINDS:
        raise CurriculumError(f"{where}: kind inválido '{kind}' (válidos: {sorted(VALID_KINDS)})")

    kb = act.get("kb_slug", "")
    academy = act.get("academy_slug", "")
    challenge = act.get("challenge_slug", "")
    gap = act.get("gap", "")

    targets = [t for t in (kb, academy, challenge) if t]
    if kind in {"theory", "lab"} and not targets and not gap:
        raise CurriculumError(f"{where}: atividade '{kind}' sem destino (kb_slug/academy_slug/challenge_slug) e sem gap declarado")
    if kind == "assessment" and not act.get("questions") and not gap:
        raise CurriculumError(f"{where}: avaliação sem 'questions' e sem gap declarado")
    if kind == "project" and not act.get("body_md") and not gap:
        raise CurriculumError(f"{where}: projeto sem 'body_md' (critérios) e sem gap declarado")

    if len(targets) > 1:
        raise CurriculumError(f"{where}: atividade aponta para mais de um destino: {targets}")

    if kb and kb not in ctx.kb_slugs:
        if not ctx.kb_imported:
            warnings.append(
                f"{where}: documento '{kb}' ainda não foi importado — execute "
                "scripts/import_kb.py para ativar esta teoria"
            )
        else:
            raise CurriculumError(f"{where}: kb_slug '{kb}' não existe na Knowledge Base")
    if academy and academy not in ctx.academy_slugs:
        raise CurriculumError(f"{where}: academy_slug '{academy}' não existe na Academy")
    if challenge and challenge not in ctx.challenge_slugs:
        raise CurriculumError(f"{where}: challenge_slug '{challenge}' não existe no catálogo")

    # Machines only belong to chain-style modules; warn if a machine is used as a
    # generic lab exercise outside its own category, to keep the curriculum honest.
    if challenge and ctx.challenge_kind.get(challenge) == "machine":
        warnings.append(f"{where}: usa a máquina '{challenge}' — confirme que o capstone não depende de um alvo já resolvido")

    for q in act.get("questions", []) or []:
        _require_keys(q, ("id", "prompt"), f"{where}.questions")
        if "answer" not in q and "accepted" not in q:
            raise CurriculumError(f"{where}.questions[{q.get('id')}]: questão sem 'answer'/'accepted'")
        _check_code_spans(where, "questions", q.get("prompt", ""))

    if "quiz" in act and not isinstance(act["quiz"], bool):
        raise CurriculumError(f"{where}: 'quiz' deve ser booleano")

    equipment = act.get("equipment", "")
    if equipment and equipment not in VALID_EQUIPMENT:
        raise CurriculumError(
            f"{where}: equipment inválido '{equipment}' (válidos: {sorted(VALID_EQUIPMENT)})"
        )
    return warnings


def _check_code_spans(where: str, label: str, value: str) -> None:
    """Short curriculum strings render through ``lp_web.inline_md``."""
    if str(value).count("`") % 2:
        raise CurriculumError(f"{where} > {label}: crase sem par (o texto depois dela viraria código): {value!r}")


def validate_curriculum(data: dict, ctx: ValidationContext, filename: str = "") -> list[str]:
    """Validate a whole path document. Raises CurriculumError on fatal problems."""
    where = f"path '{filename or data.get('slug', '?')}'"
    _require_keys(
        data,
        ("slug", "title", "summary", "entry_level", "exit_level",
         "estimated_hours", "modules", "capstone"),
        where,
    )
    if data["slug"] in ctx.seen_paths:
        raise CurriculumError(f"{where}: slug de trilha duplicado '{data['slug']}'")
    ctx.seen_paths.add(data["slug"])

    warnings: list[str] = []
    modules = data["modules"]
    if not modules:
        raise CurriculumError(f"{where}: trilha sem módulos")

    seen_module_slugs: set[str] = set()
    for mi, mod in enumerate(modules, 1):
        mwhere = f"{where} > módulo {mi}"
        _require_keys(mod, ("slug", "title", "objective", "units"), mwhere)
        if mod["slug"] in seen_module_slugs:
            raise CurriculumError(f"{mwhere}: slug de módulo duplicado '{mod['slug']}'")
        seen_module_slugs.add(mod["slug"])
        if not mod["units"]:
            raise CurriculumError(f"{mwhere}: módulo sem disciplinas (units)")
        for competency in mod.get("competencies", []) or []:
            _check_code_spans(mwhere, "competencies", competency)

        seen_unit_slugs: set[str] = set()
        for ui, unit in enumerate(mod["units"], 1):
            uwhere = f"{mwhere} > disciplina {ui}"
            _require_keys(unit, ("slug", "title", "activities"), uwhere)
            if unit["slug"] in seen_unit_slugs:
                raise CurriculumError(f"{uwhere}: slug de disciplina duplicado '{unit['slug']}'")
            seen_unit_slugs.add(unit["slug"])
            if not unit["activities"]:
                raise CurriculumError(f"{uwhere}: disciplina sem atividades")
            for ai, act in enumerate(unit["activities"], 1):
                warnings.extend(validate_activity(act, f"{uwhere} > atividade {ai}", ctx))

        # module gate must point at an earlier module of the same path
        req = mod.get("requires_module", "")
        if req and req not in seen_module_slugs - {mod["slug"]}:
            raise CurriculumError(f"{mwhere}: requires_module '{req}' não é um módulo anterior desta trilha")

    cap = data["capstone"]
    _require_keys(cap, ("objective", "success_criteria", "evidence", "grading_md"), f"{where} > capstone")
    # The capstone must be a trackable activity, otherwise the rule "path
    # completion requires the capstone" cannot be enforced.
    if not any(
        act["kind"] == "project"
        for mod in modules for unit in mod["units"] for act in unit["activities"]
    ):
        raise CurriculumError(f"{where}: capstone declarado mas nenhuma atividade 'project' o representa")
    if not cap["success_criteria"]:
        raise CurriculumError(f"{where} > capstone: sem critérios de sucesso objetivos")
    for field_name in ("success_criteria", "evidence"):
        for item in cap[field_name]:
            _check_code_spans(f"{where} > capstone", field_name, item)
    if cap.get("challenge_slug") and cap["challenge_slug"] not in ctx.challenge_slugs:
        raise CurriculumError(f"{where} > capstone: challenge_slug '{cap['challenge_slug']}' não existe")

    for prereq in data.get("prerequisites", []) or []:
        if prereq not in ctx.path_slugs and prereq != data["slug"]:
            raise CurriculumError(f"{where}: pré-requisito '{prereq}' não é uma trilha existente")

    return warnings


def collect_stats(data: dict) -> dict[str, Any]:
    """Counts used by the UI and by the acceptance checks."""
    acts = [a for m in data["modules"] for u in m["units"] for a in u["activities"]]
    by_kind: dict[str, int] = {}
    for a in acts:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    return {
        "modules": len(data["modules"]),
        "units": sum(len(m["units"]) for m in data["modules"]),
        "activities": len(acts),
        "by_kind": by_kind,
        "labs": sum(1 for a in acts if a.get("challenge_slug")),
        "kb_docs": len({a["kb_slug"] for a in acts if a.get("kb_slug")}),
        "academy": len({a["academy_slug"] for a in acts if a.get("academy_slug")}),
        "assessments": by_kind.get("assessment", 0),
        "gaps": sum(1 for a in acts if a.get("gap")),
        "minutes": sum(a.get("estimated_minutes", 15) for a in acts),
    }