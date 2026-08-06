"""Chat router — Foundry Agent Service via Responses API + agent_reference.

We invoke the versioned Foundry agent (see `app/agent.py`) through the OpenAI
Responses API on the Foundry project. The agent's Foundry IQ Knowledge Base
(MCP tool) does retrieval on the runtime, and citation annotations come back
inline in the response.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import create_or_get_agent, get_agent_name, get_project_client
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

def _openai_client():
    return get_project_client().get_openai_client()


def _agent_reference() -> dict:
    return {"agent_reference": {"name": get_agent_name(), "type": "agent_reference"}}


def _extract_citations(response) -> list[Citation]:
    """Pull URL / MCP citations from a Responses API result."""
    seen: set[tuple[str, str]] = set()
    citations: list[Citation] = []

    output = getattr(response, "output", None) or []
    for item in output:
        content = getattr(item, "content", None) or []
        for block in content:
            for ann in getattr(block, "annotations", None) or []:
                title = getattr(ann, "title", "") or getattr(ann, "filename", "") or ""
                url = getattr(ann, "url", "") or getattr(ann, "file_id", "") or ""
                excerpt = getattr(ann, "text", "") or ""
                key = (title, url)
                if (title or url) and key not in seen:
                    seen.add(key)
                    citations.append(Citation(title=title or "source", url=url, content=excerpt))
    return citations


def _response_text(response) -> str:
    txt = getattr(response, "output_text", None)
    if txt:
        return txt
    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        for block in getattr(item, "content", None) or []:
            t = getattr(block, "text", None)
            if isinstance(t, str):
                parts.append(t)
            elif t is not None:
                v = getattr(t, "value", None)
                if v:
                    parts.append(v)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Core sync call
# ---------------------------------------------------------------------------

def _run_agent_sync(conversation_id: Optional[str], message: str) -> tuple[str, list[Citation], str]:
    """Send `message` to the agent via Responses API. Returns (text, citations, conv_id)."""
    create_or_get_agent()  # idempotent — registers/refreshes the version
    client = _openai_client()

    if not conversation_id:
        conv = client.conversations.create()
        conversation_id = conv.id

    resp = client.responses.create(
        conversation=conversation_id,
        input=message,
        extra_body=_agent_reference(),
    )
    text = _response_text(resp) or ""
    citations = _extract_citations(resp)
    return text, citations, conversation_id


# ---------------------------------------------------------------------------
# POST /api/chat  (synchronous)
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    response_text, citations, conv_id = _run_agent_sync(request.thread_id, request.message)
    return ChatResponse(response=response_text, thread_id=conv_id, citations=citations)


# ---------------------------------------------------------------------------
# POST /api/chat/stream  (Server-Sent Events)
# ---------------------------------------------------------------------------

async def _stream_generator(conversation_id: Optional[str], message: str) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()

    try:
        response_text, citations, conv_id = await loop.run_in_executor(
            None, _run_agent_sync, conversation_id, message
        )
    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        error_event = StreamEvent(delta=f"Error: {exc}", thread_id=conversation_id or "", done=True)
        yield f"data: {error_event.model_dump_json()}\n\n"
        return

    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        payload = StreamEvent(delta=chunk, thread_id=conv_id)
        yield f"data: {payload.model_dump_json()}\n\n"
        await asyncio.sleep(0.02)

    final = StreamEvent(done=True, thread_id=conv_id, citations=citations)
    yield f"data: {final.model_dump_json()}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_generator(request.thread_id, request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /api/chat/threads/{thread_id}/messages  (list conversation messages)
# ---------------------------------------------------------------------------

@router.get("/threads/{thread_id}/messages", response_model=ThreadMessages)
def get_thread_messages(thread_id: str) -> ThreadMessages:
    client = _openai_client()
    try:
        items_page = client.conversations.items.list(conversation_id=thread_id, order="asc")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {exc}") from exc

    items: list[MessageItem] = []
    for it in items_page:
        role = getattr(it, "role", None) or "assistant"
        text_parts: list[str] = []
        for block in getattr(it, "content", None) or []:
            t = getattr(block, "text", None)
            if isinstance(t, str):
                text_parts.append(t)
            elif t is not None:
                v = getattr(t, "value", None)
                if v:
                    text_parts.append(v)
        items.append(
            MessageItem(
                id=getattr(it, "id", ""),
                role=role,
                content="\n".join(text_parts),
                created_at=str(getattr(it, "created_at", "")) if hasattr(it, "created_at") else None,
            )
        )
    return ThreadMessages(thread_id=thread_id, messages=items)


# ---------------------------------------------------------------------------
# DELETE /api/chat/threads/{thread_id}
# ---------------------------------------------------------------------------

@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str) -> None:
    client = _openai_client()
    try:
        client.conversations.delete(conversation_id=thread_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {exc}") from exc
