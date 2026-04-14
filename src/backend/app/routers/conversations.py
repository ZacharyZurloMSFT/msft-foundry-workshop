"""Conversations router — manage conversation threads via Foundry Agent Service."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app import conversation_store
from app.models import (
    ConversationDetail,
    ConversationMetadata,
    MessageItem,
    TitleUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _get_project_client(request: Request):
    """Extract the project client from app state, or raise 503."""
    client = getattr(request.app.state, "project_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Project client not initialized")
    return client


@router.get("", response_model=list[ConversationMetadata])
async def list_conversations() -> list[ConversationMetadata]:
    """List all active conversations, most recent first."""
    return conversation_store.list_all()


@router.post("", response_model=ConversationMetadata, status_code=201)
async def create_conversation(request: Request) -> ConversationMetadata:
    """Start a new conversation by creating a Foundry thread."""
    client = _get_project_client(request)
    thread = client.agents.threads.create()
    metadata = ConversationMetadata(
        thread_id=thread.id,
        title="New conversation",
        created_at=datetime.now(timezone.utc),
        message_count=0,
    )
    conversation_store.add(metadata)
    logger.info("Created conversation thread %s", thread.id)
    return metadata


@router.get("/{thread_id}", response_model=ConversationDetail)
async def get_conversation(thread_id: str, request: Request) -> ConversationDetail:
    """Fetch the full message history for a conversation."""
    meta = conversation_store.get(thread_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    client = _get_project_client(request)
    raw_messages = client.agents.messages.list(thread_id=thread_id)

    messages: list[MessageItem] = []
    for msg in raw_messages:
        content = ""
        if msg.content:
            # Content is a list of content blocks; extract text values
            parts = []
            for block in msg.content:
                if hasattr(block, "text") and block.text:
                    parts.append(block.text.value if hasattr(block.text, "value") else str(block.text))
            content = "\n".join(parts)
        messages.append(
            MessageItem(
                role=msg.role or "unknown",
                content=content,
                created_at=datetime.fromtimestamp(msg.created_at, tz=timezone.utc) if msg.created_at else None,
            )
        )

    return ConversationDetail(
        thread_id=thread_id,
        title=meta.title,
        messages=messages,
    )


@router.delete("/{thread_id}", status_code=204)
async def delete_conversation(thread_id: str, request: Request) -> None:
    """Delete a conversation and its Foundry thread."""
    if not conversation_store.get(thread_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    client = _get_project_client(request)
    try:
        client.agents.threads.delete(thread_id=thread_id)
    except Exception:
        logger.warning("Failed to delete Foundry thread %s — removing locally anyway", thread_id, exc_info=True)

    conversation_store.delete(thread_id)


@router.put("/{thread_id}/title", response_model=ConversationMetadata)
async def rename_conversation(thread_id: str, body: TitleUpdate) -> ConversationMetadata:
    """Update the title of an existing conversation."""
    updated = conversation_store.update_title(thread_id, body.title)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated
