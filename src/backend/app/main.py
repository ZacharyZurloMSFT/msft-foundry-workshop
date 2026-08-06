"""FastAPI application factory."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.conversations import router as conversations_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
logger = logging.getLogger(__name__)


# Retry loop for KB + agent registration. On a fresh deploy Foundry data-plane
# RBAC takes ~5-10 minutes to propagate, so both calls fail with PermissionDenied
# on the first attempt. We spin these in a background thread with retry so the
# app becomes "ready" as soon as Azure catches up, without a user having to
# manually retry a chat.
_kb_ready = False
_agent_ready = False
_last_startup_error: str = ""
STARTUP_RETRY_SECONDS = 30
STARTUP_MAX_MINUTES = 25


def _background_startup_retry() -> None:
    """Keep trying KB + agent init until success (or STARTUP_MAX_MINUTES)."""
    global _kb_ready, _agent_ready, _last_startup_error

    from app.config import settings
    if not settings.is_configured:
        logger.warning("Skipping background startup — Azure config missing.")
        return

    from app.knowledge_base import ensure_knowledge_base
    from app.agent import create_or_get_agent

    deadline = time.time() + STARTUP_MAX_MINUTES * 60
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            if not _kb_ready:
                ensure_knowledge_base()
                _kb_ready = True
                logger.info("[startup:%d] ✔ Foundry IQ knowledge base ready", attempt)
            if not _agent_ready:
                create_or_get_agent()
                _agent_ready = True
                logger.info("[startup:%d] ✔ Agent registered — backend is fully ready", attempt)
            _last_startup_error = ""
            return
        except Exception as exc:
            _last_startup_error = str(exc)
            logger.info(
                "[startup:%d] Not ready yet (%s). Sleeping %ds and retrying...",
                attempt, type(exc).__name__, STARTUP_RETRY_SECONDS,
            )
            time.sleep(STARTUP_RETRY_SECONDS)

    logger.error(
        "Startup retry gave up after %d minutes. Last error: %s",
        STARTUP_MAX_MINUTES, _last_startup_error,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up...")

    # Search index — cheap, no RBAC quirks. Do it inline.
    try:
        from app.search_index import create_or_update_index
        create_or_update_index()
        logger.info("Search index ready")
    except Exception as e:
        logger.warning("Could not create search index: %s", e)

    # Auto-seed sample documents (best-effort)
    try:
        from azure.core.exceptions import ResourceNotFoundError as RNF
        from app.routers.documents import SAMPLES_DIR, _seed_file
        from app.clients import get_search_client
        sc = get_search_client()
        if sc is not None and SAMPLES_DIR.exists():
            try:
                existing = list(sc.search(search_text="*", select=["source"], top=1))
            except RNF:
                existing = []
            if not existing:
                logger.info("Index is empty — auto-seeding sample documents...")
                for p in sorted(SAMPLES_DIR.glob("*.txt")):
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")
                        _seed_file(p.name, text, sc)
                        logger.info("Auto-seeded '%s'", p.name)
                    except Exception as e:
                        logger.warning("Could not seed '%s': %s", p.name, e)
            else:
                logger.info("Index already has documents — skipping auto-seed")
    except Exception as e:
        logger.warning("Auto-seed skipped: %s", e)

    # KB + agent registration in the background — they need Foundry data-plane
    # RBAC to have propagated, which takes ~5-10 min on a fresh deploy. Running
    # this on the request path would give the user PermissionDenied errors; the
    # background thread keeps trying so /health flips to agent_ready as soon as
    # Azure catches up.
    threading.Thread(
        target=_background_startup_retry, name="startup-retry", daemon=True
    ).start()
    logger.info("Backend HTTP is up; KB + agent init retrying in background.")

    yield
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Foundry RAG Chat API",
        description="RAG chat endpoint powered by Microsoft Foundry Agent Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        """Basic liveness — the FastAPI process is up. Always 200."""
        return {
            "status": "ok",
            "kb_ready": _kb_ready,
            "agent_ready": _agent_ready,
        }

    @app.get("/ready", tags=["health"])
    def ready() -> JSONResponse:
        """Readiness — true only once KB + agent have been registered with Foundry.

        Returns HTTP 503 while background startup is still retrying, so the
        deploy script can poll this endpoint until Foundry RBAC has propagated.
        """
        if _kb_ready and _agent_ready:
            return JSONResponse(
                status_code=200,
                content={"ready": True, "kb_ready": True, "agent_ready": True},
            )
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "kb_ready": _kb_ready,
                "agent_ready": _agent_ready,
                "last_error": _last_startup_error or None,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all so Azure SDK errors return JSON 500 (with CORS headers) instead of crashing."""
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
