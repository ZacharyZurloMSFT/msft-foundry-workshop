"""Documents router — upload, list, and delete indexed documents."""

import logging
import os

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.clients import get_project_client, get_search_client
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
    import io
    text = extract_text(io.BytesIO(content), file.filename)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text content could be extracted from the file")

    # Chunk
    chunks = chunk_text(text)
    logger.info("Extracted %d chunks from '%s'", len(chunks), file.filename)

    # Embed
    project_client = get_project_client()
    embeddings = generate_embeddings(chunks, project_client)

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

    results = search_client.search(
        search_text="*",
        select=["source", "chunk_index"],
        top=1000,
    )

    # Aggregate by source
    docs: dict[str, int] = {}
    for r in results:
        source = r.get("source", "unknown")
        docs[source] = docs.get(source, 0) + 1

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
