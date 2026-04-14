"""Pydantic models for chat API request/response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    message: str = Field(..., min_length=1, description="User message to send to the agent")
    thread_id: Optional[str] = Field(None, description="Existing thread ID to continue conversation")


class Citation(BaseModel):
    """A source citation returned by the RAG agent."""

    title: str = Field(..., description="Document title")
    url: str = Field("", description="Source URL")
    content: str = Field("", description="Relevant excerpt from the source")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    response: str = Field(..., description="Agent response text")
    thread_id: str = Field(..., description="Thread ID for continuing the conversation")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")


class StreamEvent(BaseModel):
    """A single SSE event in the streaming response."""

    delta: str = Field("", description="Text chunk")
    thread_id: str = Field("", description="Thread ID")
    done: bool = Field(False, description="Whether the stream is complete")
    citations: list[Citation] = Field(default_factory=list, description="Citations (sent with final event)")


class MessageItem(BaseModel):
    """A single message in a thread."""

    id: str
    role: str
    content: str
    created_at: Optional[str] = None


class ThreadMessages(BaseModel):
    """Response for thread message history."""

    thread_id: str
    messages: list[MessageItem]


# ─── Document Models ───────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response after uploading and indexing a document."""
    filename: str
    chunks: int
    status: str = "indexed"


class DocumentInfo(BaseModel):
    """Metadata about an indexed document."""
    filename: str
    chunk_count: int
    indexed_at: Optional[str] = None


class SearchDocument(BaseModel):
    """A document chunk stored in Azure AI Search."""
    id: str
    content: str
    content_vector: Optional[list] = None
    title: str
    source: str
    chunk_index: int
    indexed_at: Optional[str] = None


# ─── Conversation Models ───────────────────────────────────────────

class ConversationMetadata(BaseModel):
    """Metadata for a conversation thread."""
    thread_id: str
    title: str
    created_at: str
    message_count: int = 0


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    thread_id: str
    title: str
    messages: list = []


class TitleUpdate(BaseModel):
    """Request to update a conversation title."""
    title: str
