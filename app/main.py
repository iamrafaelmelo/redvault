"""Application factory and middleware."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR, TEMPLATE_DIR, ensure_dirs
from .database import init_db, SessionLocal
from .lab_manager import lab_manager
from .security import apply_session_cookie, decode_flash, local_user
from .content import seed_platform_content
from .lp_web import router as learning_paths_router
from .web import router as web_router
from .api import router as api_router
from .internal import router as internal_router

logger = logging.getLogger("redvault")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    init_db()
    with SessionLocal() as db:
        local_user(db)
        result = seed_platform_content(db)
        if result["errors"]:
            for error in result["errors"]:
                logger.warning("content: %s", error)
        logger.info("content synced: %s challenges", result["challenges"])
    # Knowledge base: categories, challenge links, search index (idempotent).
    try:
        from .kb_import import register_sources
        from .kb_own import sync_own_documents
        from .kb_search import ensure_index, rebuild
        from .kb_seed import seed_all

        with SessionLocal() as db:
            register_sources(db)
            kb_stats = seed_all(db)
            own_docs = sync_own_documents(db)
            db.commit()
        ensure_index()
        rebuild()
        logger.info("kb synced: %s categories, %s payloads, %s challenge links, %s own docs",
                    kb_stats["categories"], kb_stats["payloads"], kb_stats["challenge_links"], own_docs)
    except Exception as exc:  # noqa: BLE001 - kb must never block boot
        logger.warning("kb seed skipped: %s", exc)
    # Learning paths: validated curricula (a broken reference aborts loudly).
    try:
        from .lp_seed import seed_all as seed_learning_paths

        with SessionLocal() as db:
            lp_stats = seed_learning_paths(db)
        for warning in lp_stats["warnings"]:
            logger.warning("learning-path: %s", warning)
        logger.info("learning paths synced: %s trilhas, %s módulos, %s atividades",
                    lp_stats["paths"], lp_stats["modules"], lp_stats["activities"])
    except Exception as exc:  # noqa: BLE001 - curriculum error must be visible, not fatal
        logger.error("learning paths NOT loaded: %s", exc)
    lab_manager.reconcile_startup()
    yield
    lab_manager.shutdown()


app = FastAPI(
    title="REDVAULT",
    description="Private offensive security training lab",
    version="0.9.0",
    docs_url="/api/docs" if __import__("os").environ.get("REDVAULT_DEV") else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(web_router)
app.include_router(learning_paths_router)
app.include_router(api_router)
app.include_router(internal_router)


@app.middleware("http")
async def security_and_flash(request: Request, call_next):
    request.state.flashes = decode_flash(request.cookies.get("rv_flash"))
    response = await call_next(request)
    apply_session_cookie(response, request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if not request.url.path.startswith("/api/docs"):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
    if request.state.flashes:
        set_cookies = response.headers.getlist("set-cookie")
        if not any("rv_flash=" in value for value in set_cookies):
            response.delete_cookie("rv_flash", path="/")
    return response


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    from .web import templates
    from .deps import common_context
    from .database import SessionLocal

    with SessionLocal() as db:
        from .security import current_user

        user = current_user(request, db)
        context = common_context(request, db, user, "")
    return templates.TemplateResponse(request=request, name="404.html", context=context, status_code=404)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"ok": True, "app": "redvault", "labs": len(lab_manager.active_labs())}
