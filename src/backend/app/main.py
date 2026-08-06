"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.conversations import router as conversations_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up...")
    
    # Ensure search index exists
    try:
        from app.search_index import create_or_update_index
        create_or_update_index()
        logger.info("Search index ready")
    except Exception as e:
        logger.warning("Could not create search index: %s", e)

    # Register the AI Search index as a Foundry Knowledge Source (Foundry IQ).
    # Shows up under Knowledge in the Foundry portal and is what the agent uses
    # for retrieval instead of a custom search_documents function tool.
    from app.config import settings
    if settings.is_configured:
        try:
            from app.knowledge import ensure_search_knowledge_source
            ensure_search_knowledge_source()
            logger.info("Foundry knowledge source ready")
        except Exception as e:
            logger.warning(
                "Knowledge source registration failed (agent may still work with older config): %s",
                e,
            )

    # Create or find the RAG agent eagerly so it's visible in the Foundry portal
    # and available without delay on the first chat request.
    # Runs as the container's managed identity (Azure AI Developer role).
    if settings.is_configured:
        try:
            from app.agent import create_or_get_agent
            create_or_get_agent()
            logger.info("Agent ready")
        except Exception as e:
            logger.warning(
                "Agent initialization failed at startup (will retry on first chat): %s", e
            )
    
    # Seed sample documents if the index is empty (best-effort)
    try:
        from azure.core.exceptions import ResourceNotFoundError as RNF
        from app.routers.documents import SAMPLES_DIR, _seed_file
        from app.clients import get_search_client
        sc = get_search_client()
        if sc is not None and SAMPLES_DIR.exists():
            try:
                existing = list(sc.search(search_text="*", select=["source"], top=1))
            except RNF:
                existing = []  # Index not ready yet — skip auto-seed; /seed endpoint will create it on demand
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

    logger.info("Backend ready")
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
        from app.agent import _agent_id
        return {"status": "ok", "agent_id": _agent_id}

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
