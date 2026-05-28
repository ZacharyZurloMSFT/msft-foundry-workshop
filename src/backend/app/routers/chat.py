"""Chat router — RAG chat endpoints powered by Foundry Agent Service.

Flow:
  1. User message → thread → agent run created.
  2. Agent decides to call `search_documents` → run pauses (requires_action).
  3. Backend executes the real Azure AI Search query, returns formatted results.
  4. Results submitted back → agent composes final answer.
  5. Response streamed word-by-word to the frontend via Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent import create_or_get_agent, get_agents_client
from app.clients import get_search_client
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
# Search execution — called when the agent invokes the search_documents tool
# ---------------------------------------------------------------------------

def _execute_search(query: str) -> str:
    """Run an AI Search keyword query and return formatted results."""
    client = get_search_client()
    if client is None:
        return "Search service is not available."

    try:
        results = client.search(
            search_text=query,
            top=5,
            select=["content", "title", "source"],
        )
        chunks: list[str] = []
        for r in results:
            title = r.get("title") or r.get("source") or "unknown"
            content = r.get("content", "")
            chunks.append(f"[{title}]\n{content}")

        if not chunks:
            return "No relevant documents found for this query."

        return "\n\n---\n\n".join(chunks)

    except Exception as exc:
        logger.error("AI Search query failed: %s", exc)
        return f"Search failed: {exc}"


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


# ---------------------------------------------------------------------------
# Core agent run — synchronous, handles tool calls in a polling loop
# ---------------------------------------------------------------------------

def _run_agent_sync(thread_id: str, message: str) -> tuple[str, str]:
    """Run the agent to completion, handle tool calls, return (response_text, thread_id).

    This function blocks until the agent run is done or fails.  It is always
    called from an asyncio executor so it never blocks the event loop.
    """
    from azure.ai.agents.models import ToolOutput

    agents_client = get_agents_client()
    agent_id = create_or_get_agent()

    # Add the user message to the thread
    agents_client.messages.create(thread_id=thread_id, role="user", content=message)

    # Start the run
    run = agents_client.runs.create(thread_id=thread_id, agent_id=agent_id)
    logger.info("Agent run started: %s (thread=%s)", run.id, thread_id)

    # Poll until the run completes or needs a tool call
    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(1)
        run = agents_client.runs.get(thread_id=thread_id, run_id=run.id)

        if run.status == "requires_action":
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            outputs: list[ToolOutput] = []

            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments or "{}")
                logger.info("Tool call: %s(%s)", fn_name, fn_args)

                if fn_name == "search_documents":
                    result = _execute_search(fn_args.get("query", ""))
                else:
                    result = f"Unknown tool: {fn_name}"

                outputs.append(ToolOutput(tool_call_id=tc.id, output=result))

            # Submit results and let the run continue
            run = agents_client.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=outputs
            )

    if run.status != "completed":
        error = getattr(run, "last_error", run.status)
        raise Exception(f"Agent run failed: {error}")

    # Retrieve the latest assistant message
    for msg in agents_client.messages.list(thread_id=thread_id, order="desc"):
        if msg.role == "assistant":
            return _get_text_content(msg), thread_id

    return "", thread_id


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

    response_text, thread_id = _run_agent_sync(thread_id, request.message)

    return ChatResponse(response=response_text, thread_id=thread_id, citations=[])


# ---------------------------------------------------------------------------
# POST /api/chat/stream  (Server-Sent Events)
# ---------------------------------------------------------------------------

async def _stream_generator(thread_id: str, message: str) -> AsyncGenerator[str, None]:
    """Run the agent in a thread pool, then stream the response word-by-word."""
    loop = asyncio.get_event_loop()

    try:
        response_text, _ = await loop.run_in_executor(
            None, _run_agent_sync, thread_id, message
        )
    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        error_event = StreamEvent(delta=f"Error: {exc}", thread_id=thread_id, done=True)
        yield f"data: {error_event.model_dump_json()}\n\n"
        return

    # Stream the response word by word for a natural feel
    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        payload = StreamEvent(delta=chunk, thread_id=thread_id)
        yield f"data: {payload.model_dump_json()}\n\n"
        await asyncio.sleep(0.02)

    final = StreamEvent(done=True, thread_id=thread_id, citations=[])
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
