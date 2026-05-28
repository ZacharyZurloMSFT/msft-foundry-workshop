"""Documents router — upload, list, delete, and seed indexed documents."""

import io
import logging
import os
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from fastapi import APIRouter, HTTPException, UploadFile, status

from app.clients import get_search_client
from app.ingestion import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    build_search_documents,
    chunk_text,
    delete_documents_by_source,
    extract_text,
    generate_embeddings,
    index_documents,
)
from app.models import DocumentInfo, DocumentUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile) -> DocumentUploadResponse:
    """Upload a document, extract text, chunk, embed, and index it."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS.keys())}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Extract text
    text = extract_text(io.BytesIO(content), file.filename)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content could be extracted from the file")

    # Chunk
    chunks = chunk_text(text)
    logger.info("Extracted %d chunks from '%s'", len(chunks), file.filename)

    # Embed
    try:
        embeddings = generate_embeddings(chunks)
    except Exception as exc:
        logger.error("Embedding generation failed for '%s': %s", file.filename, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding generation failed: {exc}",
        ) from exc

    # Build search documents and index
    search_docs = build_search_documents(file.filename, chunks, embeddings)
    search_client = get_search_client()
    if search_client is None:
        raise HTTPException(status_code=503, detail="Search service not configured")

    index_documents(search_client, search_docs)

    return DocumentUploadResponse(
        filename=file.filename,
        chunks=len(chunks),
        status="indexed",
    )


@router.get("", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    """List all indexed documents with their chunk counts."""
    search_client = get_search_client()
    if search_client is None:
        raise HTTPException(status_code=503, detail="Search service not configured")

    try:
        results = search_client.search(
            search_text="*",
            select=["source", "chunk_index"],
            top=1000,
        )
        docs: dict[str, int] = {}
        for r in results:
            source = r.get("source", "unknown")
            docs[source] = docs.get(source, 0) + 1
    except ResourceNotFoundError:
        # Index doesn't exist yet — return empty list
        return []

    return [
        DocumentInfo(filename=source, chunk_count=count)
        for source, count in sorted(docs.items())
    ]


@router.delete("/{filename}", status_code=status.HTTP_200_OK)
async def delete_document(filename: str) -> dict[str, str | int]:
    """Delete all indexed chunks for a given document."""
    search_client = get_search_client()
    if search_client is None:
        raise HTTPException(status_code=503, detail="Search service not configured")

    deleted = delete_documents_by_source(search_client, filename)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"No document found with filename '{filename}'")

    return {"filename": filename, "deleted_chunks": deleted, "status": "deleted"}


SAMPLES_DIR = Path("/app/samples")


def _seed_file(filename: str, text: str, search_client) -> int:
    """Index a single text file; returns number of chunks indexed."""
    chunks = chunk_text(text)
    embeddings = generate_embeddings(chunks)
    docs = build_search_documents(filename, chunks, embeddings)
    index_documents(search_client, docs)
    return len(chunks)


@router.post("/seed", response_model=dict, status_code=status.HTTP_200_OK)
async def seed_sample_documents(force: bool = False) -> dict:
    """Load bundled sample documents into the index.

    Set ``force=true`` to re-index even if a document already exists.
    """
    search_client = get_search_client()
    if search_client is None:
        raise HTTPException(status_code=503, detail="Search service not configured")

    if not SAMPLES_DIR.exists():
        raise HTTPException(status_code=404, detail="No bundled sample documents found in image")

    # Gather names already indexed so we can skip them (unless force)
    if not force:
        try:
            existing_results = search_client.search(
                search_text="*", select=["source"], top=1000
            )
            existing: set[str] = {r.get("source", "") for r in existing_results}
        except ResourceNotFoundError:
            # Index doesn't exist yet — create it first, then seed everything
            logger.info("Index not found — creating it before seeding")
            try:
                from app.search_index import create_or_update_index
                create_or_update_index()
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Could not create search index: {exc}",
                ) from exc
            existing = set()
    else:
        existing = set()

    seeded: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for sample_path in sorted(SAMPLES_DIR.glob("*.txt")):
        name = sample_path.name
        if name in existing:
            skipped.append(name)
            continue
        try:
            text = sample_path.read_text(encoding="utf-8", errors="replace")
            _seed_file(name, text, search_client)
            seeded.append(name)
            logger.info("Seeded sample document '%s'", name)
        except Exception as exc:
            logger.error("Failed to seed '%s': %s", name, exc)
            errors.append(f"{name}: {exc}")

    return {
        "seeded": seeded,
        "skipped": skipped,
        "errors": errors,
        "total_seeded": len(seeded),
    }
