"""Chat router — RAG chat endpoints powered by Foundry Agent Service.

Retrieval is grounded through the Foundry IQ knowledge source attached to the
agent (see `app/agent.py`). The runtime performs the AI Search query itself and
attaches citations as message annotations — the backend just polls until the
run completes and returns the assistant message + citations.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import create_or_get_agent, get_agents_client
from app.models import (
    ChatRequest,
    ChatResponse,
    Citation,
    MessageItem,
    StreamEvent,
    ThreadMessages,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_text_content(message) -> str:
    """Extract plain text from an agent message's content blocks."""
    parts: list[str] = []
    for block in message.content:
        if hasattr(block, "text"):
            text_val = block.text
            parts.append(text_val.value if hasattr(text_val, "value") else str(text_val))
    return "\n".join(parts) if parts else ""


def _extract_citations(message) -> list[Citation]:
    """Pull URL / file citations from a message's text annotations.

    The Foundry Agents runtime emits `url_citation` and `file_citation`
    annotations on assistant messages when a knowledge source is used.
    """
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()

    for block in getattr(message, "content", []) or []:
        text_val = getattr(block, "text", None)
        if text_val is None:
            continue
        for ann in getattr(text_val, "annotations", []) or []:
            title = ""
            url = ""
            excerpt = getattr(ann, "text", "") or ""

            url_cit = getattr(ann, "url_citation", None)
            file_cit = getattr(ann, "file_citation", None)

            if url_cit is not None:
                title = getattr(url_cit, "title", "") or ""
                url = getattr(url_cit, "url", "") or ""
            elif file_cit is not None:
                title = getattr(file_cit, "file_name", "") or getattr(file_cit, "title", "") or ""
                url = getattr(file_cit, "file_id", "") or ""

            key = (title, url)
            if title and key not in seen:
                seen.add(key)
                citations.append(Citation(title=title, url=url, content=excerpt))

    return citations


# ---------------------------------------------------------------------------
# Core agent run — synchronous, waits for completion
# ---------------------------------------------------------------------------

def _run_agent_sync(thread_id: str, message: str) -> tuple[str, list[Citation], str]:
    """Run the agent to completion and return (response_text, citations, thread_id).

    Blocks until the run is done or fails. Always called from an executor so it
    never blocks the event loop.
    """
    agents_client = get_agents_client()
    agent_id = create_or_get_agent()

    agents_client.messages.create(thread_id=thread_id, role="user", content=message)

    run = agents_client.runs.create(thread_id=thread_id, agent_id=agent_id)
    logger.info("Agent run started: %s (thread=%s)", run.id, thread_id)

    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(1)
        run = agents_client.runs.get(thread_id=thread_id, run_id=run.id)

    if run.status != "completed":
        error = getattr(run, "last_error", run.status)
        raise Exception(f"Agent run failed: {error}")

    # Grab the latest assistant message
    for msg in agents_client.messages.list(thread_id=thread_id, order="desc"):
        if msg.role == "assistant":
            return _get_text_content(msg), _extract_citations(msg), thread_id

    return "", [], thread_id


# ---------------------------------------------------------------------------
# POST /api/chat  (synchronous)
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the RAG agent and return the complete response."""
    agents_client = get_agents_client()

    thread_id = request.thread_id
    if not thread_id:
        thread = agents_client.threads.create()
        thread_id = thread.id

    response_text, citations, thread_id = _run_agent_sync(thread_id, request.message)

    return ChatResponse(response=response_text, thread_id=thread_id, citations=citations)


# ---------------------------------------------------------------------------
# POST /api/chat/stream  (Server-Sent Events)
# ---------------------------------------------------------------------------

async def _stream_generator(thread_id: str, message: str) -> AsyncGenerator[str, None]:
    """Run the agent in a thread pool, then stream the response word-by-word."""
    loop = asyncio.get_event_loop()

    try:
        response_text, citations, _ = await loop.run_in_executor(
            None, _run_agent_sync, thread_id, message
        )
    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        error_event = StreamEvent(delta=f"Error: {exc}", thread_id=thread_id, done=True)
        yield f"data: {error_event.model_dump_json()}\n\n"
        return

    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        payload = StreamEvent(delta=chunk, thread_id=thread_id)
        yield f"data: {payload.model_dump_json()}\n\n"
        await asyncio.sleep(0.02)

    final = StreamEvent(done=True, thread_id=thread_id, citations=citations)
    yield f"data: {final.model_dump_json()}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream a response from the RAG agent via Server-Sent Events."""
    agents_client = get_agents_client()

    thread_id = request.thread_id
    if not thread_id:
        loop = asyncio.get_event_loop()
        thread = await loop.run_in_executor(None, agents_client.threads.create)
        thread_id = thread.id

    return StreamingResponse(
        _stream_generator(thread_id, request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /api/chat/threads/{thread_id}/messages
# ---------------------------------------------------------------------------

@router.get("/threads/{thread_id}/messages", response_model=ThreadMessages)
def get_thread_messages(thread_id: str) -> ThreadMessages:
    """Retrieve all messages in a conversation thread."""
    agents_client = get_agents_client()

    try:
        messages = agents_client.messages.list(thread_id=thread_id, order="asc")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Thread not found: {exc}") from exc

    items: list[MessageItem] = [
        MessageItem(
            id=msg.id,
            role=msg.role,
            content=_get_text_content(msg),
            created_at=str(msg.created_at) if hasattr(msg, "created_at") else None,
        )
        for msg in messages
    ]

    return ThreadMessages(thread_id=thread_id, messages=items)


# ---------------------------------------------------------------------------
# DELETE /api/chat/threads/{thread_id}
# ---------------------------------------------------------------------------

@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str) -> None:
    """Delete a conversation thread."""
    agents_client = get_agents_client()
    try:
        agents_client.threads.delete(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Thread not found: {exc}") from exc
