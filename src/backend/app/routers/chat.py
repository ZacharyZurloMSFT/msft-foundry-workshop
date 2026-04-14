"""Chat router — RAG chat endpoints powered by Foundry Agent Service."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import create_or_get_agent, get_project_client
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


def _extract_citations(message) -> list[Citation]:
    """Extract citations from an agent message if present."""
    citations: list[Citation] = []
    if not hasattr(message, "url_citation_annotations"):
        return citations
    for annotation in getattr(message, "url_citation_annotations", []) or []:
        citations.append(
            Citation(
                title=getattr(annotation, "title", ""),
                url=getattr(annotation, "url", ""),
                content=getattr(annotation, "content", ""),
            )
        )
    return citations


def _get_text_content(message) -> str:
    """Extract plain text from a message's content blocks."""
    parts: list[str] = []
    for block in message.content:
        if hasattr(block, "text"):
            text_val = block.text
            if hasattr(text_val, "value"):
                parts.append(text_val.value)
            else:
                parts.append(str(text_val))
    return "\n".join(parts) if parts else ""


# ---- POST /api/chat --------------------------------------------------------

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the RAG agent and get a response."""
    client = get_project_client()
    agent_id = create_or_get_agent()

    # Thread management
    if request.thread_id:
        thread_id = request.thread_id
    else:
        thread = client.agents.threads.create()
        thread_id = thread.id

    # Add user message
    client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=request.message,
    )

    # Run the agent
    run = client.agents.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id,
    )

    if run.status == "failed":
        raise HTTPException(status_code=502, detail=f"Agent run failed: {run.last_error}")

    # Retrieve assistant response
    messages = client.agents.messages.list(thread_id=thread_id, order="desc", limit=1)
    assistant_msg = None
    for msg in messages.data:
        if msg.role == "assistant":
            assistant_msg = msg
            break

    if assistant_msg is None:
        raise HTTPException(status_code=502, detail="No assistant response received")

    response_text = _get_text_content(assistant_msg)
    citations = _extract_citations(assistant_msg)

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        citations=citations,
    )


# ---- POST /api/chat/stream -------------------------------------------------

async def _stream_generator(thread_id: str, agent_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE events from a streaming agent run."""
    client = get_project_client()

    with client.agents.runs.stream(
        thread_id=thread_id,
        agent_id=agent_id,
    ) as stream:
        for event_type, event_data, *_ in stream:
            if event_type == "thread.message.delta":
                delta = ""
                if hasattr(event_data, "delta") and event_data.delta.content:
                    for block in event_data.delta.content:
                        if hasattr(block, "text") and hasattr(block.text, "value"):
                            delta += block.text.value
                if delta:
                    payload = StreamEvent(delta=delta, thread_id=thread_id)
                    yield f"data: {payload.model_dump_json()}\n\n"

    # Final event
    messages = client.agents.messages.list(thread_id=thread_id, order="desc", limit=1)
    citations: list[Citation] = []
    for msg in messages.data:
        if msg.role == "assistant":
            citations = _extract_citations(msg)
            break

    final = StreamEvent(done=True, thread_id=thread_id, citations=citations)
    yield f"data: {final.model_dump_json()}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream a response from the RAG agent via Server-Sent Events."""
    client = get_project_client()
    agent_id = create_or_get_agent()

    if request.thread_id:
        thread_id = request.thread_id
    else:
        thread = client.agents.threads.create()
        thread_id = thread.id

    client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=request.message,
    )

    return StreamingResponse(
        _stream_generator(thread_id, agent_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---- GET /api/chat/threads/{thread_id}/messages ----------------------------

@router.get("/threads/{thread_id}/messages", response_model=ThreadMessages)
def get_thread_messages(thread_id: str) -> ThreadMessages:
    """Retrieve all messages in a conversation thread."""
    client = get_project_client()

    try:
        messages = client.agents.messages.list(thread_id=thread_id, order="asc")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Thread not found: {exc}") from exc

    items: list[MessageItem] = []
    for msg in messages.data:
        items.append(
            MessageItem(
                id=msg.id,
                role=msg.role,
                content=_get_text_content(msg),
                created_at=str(msg.created_at) if hasattr(msg, "created_at") else None,
            )
        )

    return ThreadMessages(thread_id=thread_id, messages=items)


# ---- DELETE /api/chat/threads/{thread_id} -----------------------------------

@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str) -> None:
    """Delete a conversation thread."""
    client = get_project_client()
    try:
        client.agents.threads.delete(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Thread not found: {exc}") from exc
