"""Server-side flag derivation and validation.

Flag values are deterministically derived from the master secret, challenge
slug and flag key. They are never stored in SQLite or shipped to the platform
frontend. Lab processes receive only their own values at runtime.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import load_secret
from .models import Challenge, Flag, ObjectiveState

_SECRET = load_secret()


def derive_flag(challenge_slug: str, flag_key: str) -> str:
    digest = hmac.new(_SECRET, f"flag:{challenge_slug}:{flag_key}".encode(), hashlib.sha256).digest()
    token = base64.b32encode(digest[:15]).decode().rstrip("=").lower()
    return f"RV{{{challenge_slug.split('-')[0]}_{token}}}"


def flag_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode()).hexdigest()


def mask_value(value: str) -> str:
    value = value.strip()
    if len(value) <= 10:
        return value[:3] + "***"
    return value[:6] + "…" + value[-4:]


def validate_flag(db: Session, user_id: int, challenge: Challenge, flag: Flag, submitted: str) -> tuple[bool, str]:
    expected = derive_flag(challenge.slug, flag.key)
    if not hmac.compare_digest(expected, submitted.strip()):
        return False, "Este valor não corresponde a nenhuma flag deste alvo."
    if flag.requires_objective:
        state = db.scalar(
            select(ObjectiveState).where(
                ObjectiveState.user_id == user_id,
                ObjectiveState.challenge_id == challenge.id,
                ObjectiveState.flag_key == flag.key,
            )
        )
        if not state or not state.met:
            return False, "Valor de flag reconhecido, mas o lab não registrou o estado de exploração exigido. Reproduza o objetivo no ambiente em execução."
    return True, "Flag aceita."


def mark_objective(db: Session, user_id: int, challenge_id: int, flag_key: str, evidence: str = "") -> ObjectiveState:
    # Read with the ORM but write with a literal UPSERT: the runner calls this
    # from more than one place (HTTP callback, bot, CLI repair) and two writers
    # racing on ``if not state: db.add(...)`` used to create duplicate rows for
    # the same (user, challenge, flag) triple. The unique key is the triple, so
    # the second writer updates instead of inserting.
    now = datetime.now(timezone.utc)
    text_evidence = (evidence or "objetivo executado")[:300]
    if db.get_bind().dialect.name == "sqlite":
        db.execute(
            text(
                """
                INSERT INTO objective_states
                    (user_id, challenge_id, flag_key, met, met_at, evidence)
                VALUES (:user_id, :challenge_id, :flag_key, 1, :now, :evidence)
                ON CONFLICT(user_id, challenge_id, flag_key) DO UPDATE SET
                    met = 1, met_at = excluded.met_at, evidence = excluded.evidence
                """
            ),
            {
                "user_id": user_id,
                "challenge_id": challenge_id,
                "flag_key": flag_key,
                "now": now,
                "evidence": text_evidence,
            },
        )
        state = db.scalar(
            select(ObjectiveState).where(
                ObjectiveState.user_id == user_id,
                ObjectiveState.challenge_id == challenge_id,
                ObjectiveState.flag_key == flag_key,
            )
        )
        db.flush()
        return state

    state = db.scalar(
        select(ObjectiveState).where(
            ObjectiveState.user_id == user_id,
            ObjectiveState.challenge_id == challenge_id,
            ObjectiveState.flag_key == flag_key,
        )
    )
    if not state:
        state = ObjectiveState(user_id=user_id, challenge_id=challenge_id, flag_key=flag_key)
        db.add(state)
    state.met = True
    state.met_at = now
    state.evidence = text_evidence
    db.flush()
    return state
