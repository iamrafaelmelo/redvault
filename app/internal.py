"""Internal lab-to-platform callbacks. Not part of the public UI API."""
from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends

from .bot import BotError, run_bot
from .deps import get_db
from .flags import mark_objective
from .lab_manager import lab_manager
from .traffic import lab_traffic
from .models import Activity, Challenge, LabSession, ObjectiveState

logger = logging.getLogger("redvault.internal")

router = APIRouter(prefix="/internal", include_in_schema=False)


def _session_from_token(db: Session, token: str) -> LabSession:
    if not token or len(token) > 128:
        raise HTTPException(status_code=403, detail="token inválido")
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(LabSession).where(LabSession.token_hash == digest))
    if not row:
        raise HTTPException(status_code=403, detail="lab desconhecido")
    lab = lab_manager.get(row.id)
    if not lab:
        raise HTTPException(status_code=403, detail="lab não está ativo")
    return row


@router.post("/lab-traffic", include_in_schema=False)
async def lab_traffic_ping(request: Request, db: Session = Depends(get_db)):
    """Called by the lab proxy for every request it forwards.

    Keeps the idle reaper honest (traffic from another machine counts as
    activity) and returns the current rate so the proxy can report abuse.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="corpo inválido") from exc
    row = _session_from_token(db, str(body.get("token", "")))
    lab_manager.touch(row.id)
    try:
        count = max(1, min(int(body.get("count", 1)), 100_000))
    except (TypeError, ValueError):
        count = 1
    stats = lab_traffic.record(row.id, count)
    if stats["first_abort"]:
        challenge = db.get(Challenge, row.challenge_id)
        db.add(Activity(
            user_id=row.user_id,
            kind="lab_abuse",
            message=f"Tráfego excessivo contra {challenge.title if challenge else row.challenge_id} "
                    f"({stats['rps']}/s)",
            challenge_id=row.challenge_id,
            meta={"rps": stats["rps"], "port": row.port},
        ))
        db.commit()
    return {"ok": True, **stats}


@router.post("/lab-callback")
async def lab_callback(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="corpo inválido") from exc
    token = str(body.get("token", ""))
    try:
        row = _session_from_token(db, token)
    except HTTPException as exc:
        # The lab only logs a boolean, so the reason has to reach the server log.
        # uvicorn only shows ``redvault.*`` loggers at WARNING, so this line is
        # visible in the standard service log.
        logger.warning(
            "lab-callback rejected (HTTP %s): session=%s key=%r", exc.status_code,
            body.get("session"), body.get("flag_key"),
        )
        raise
    challenge = db.get(Challenge, row.challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="desafio ausente")
    flag_key = str(body.get("flag_key", ""))[:40]
    valid_keys = {flag.key for flag in challenge.flags}
    if flag_key not in valid_keys:
        raise HTTPException(status_code=400, detail="objetivo desconhecido")
    evidence = str(body.get("evidence", ""))[:300]
    mark_objective(db, row.user_id, challenge.id, flag_key, evidence=evidence)
    db.add(Activity(
        user_id=row.user_id,
        kind="objective_met",
        message=f"Estado de exploração registrado em {challenge.title}",
        challenge_id=challenge.id,
        meta={"flag_key": flag_key, "evidence": evidence},
    ))
    db.commit()
    return {"ok": True, "objective": flag_key}


@router.post("/bot")
async def run_lab_bot(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="corpo inválido") from exc
    row = _session_from_token(db, str(body.get("token", "")))
    target = str(body.get("url", "")).strip()
    if not target.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL de alvo inválida")
    cookies = body.get("cookies") or []
    if not isinstance(cookies, list) or len(cookies) > 8:
        raise HTTPException(status_code=400, detail="cookies inválidos")
    safe_cookies = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", name) or len(value) > 500:
            continue
        safe_cookies.append({"name": name, "value": value, "httpOnly": False})
    lab = lab_manager.get(row.id)
    if not lab:
        raise HTTPException(status_code=409, detail="lab não está ativo")
    try:
        # Selenium is blocking for as long as the browser is open (5+ s). Running
        # it on the event loop froze the whole platform: the lab's own callback
        # (XSS -> /collect -> objective) timed out while the bot was still
        # visiting, so no XSS lab could ever register its objective.
        result = await run_in_threadpool(
            run_bot, target, expected_port=lab.port, cookies=safe_cookies
        )
    except BotError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result
