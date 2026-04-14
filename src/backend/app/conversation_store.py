"""In-memory conversation store.

For workshop simplicity this uses a plain dict guarded by a threading lock.
In production you would swap this for Cosmos DB or another persistent store.
"""

import threading
from datetime import datetime

from app.models import ConversationMetadata

_lock = threading.Lock()
_conversations: dict[str, ConversationMetadata] = {}


def add(metadata: ConversationMetadata) -> None:
    """Store a new conversation."""
    with _lock:
        _conversations[metadata.thread_id] = metadata


def get(thread_id: str) -> ConversationMetadata | None:
    """Return metadata for a single conversation, or None."""
    with _lock:
        return _conversations.get(thread_id)


def list_all() -> list[ConversationMetadata]:
    """Return all conversations sorted by most recent first."""
    with _lock:
        return sorted(
            _conversations.values(),
            key=lambda c: c.created_at,
            reverse=True,
        )


def delete(thread_id: str) -> bool:
    """Remove a conversation. Returns True if it existed."""
    with _lock:
        return _conversations.pop(thread_id, None) is not None


def update_title(thread_id: str, title: str) -> ConversationMetadata | None:
    """Update the title of an existing conversation."""
    with _lock:
        conv = _conversations.get(thread_id)
        if conv is None:
            return None
        conv.title = title
        return conv


def increment_message_count(thread_id: str, delta: int = 1) -> None:
    """Bump the message count for a conversation."""
    with _lock:
        conv = _conversations.get(thread_id)
        if conv:
            conv.message_count += delta
