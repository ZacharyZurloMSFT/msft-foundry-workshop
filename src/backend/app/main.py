"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    
    # Create or find the RAG agent eagerly so it's visible in the Foundry portal
    # and available without delay on the first chat request.
    # Runs as the container's managed identity (Azure AI Developer role).
    from app.config import settings
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
        from app.routers.documents import SAMPLES_DIR, _seed_file
        from app.clients import get_search_client
        from app.ingestion import chunk_text, generate_embeddings, build_search_documents, index_documents
        sc = get_search_client()
        if sc is not None and SAMPLES_DIR.exists():
            existing = list(sc.search(search_text="*", select=["source"], top=1))
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

    return app


app = create_app()
