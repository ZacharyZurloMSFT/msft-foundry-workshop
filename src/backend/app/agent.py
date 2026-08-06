"""Foundry Agent Service — versioned agent lifecycle.

The New Foundry uses **versioned agents** created via
`AIProjectClient.agents.create_version(...)` with a `PromptAgentDefinition`,
and invoked via the **Responses API** using an `agent_reference` (see chat.py).

This module only manages the portal-registered agent version — there is no
separate runtime `asst_xxx` agent because the MCP tool (for our Foundry IQ
Knowledge Base) is not supported by the legacy Assistants API.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings
from app.knowledge_base import ensure_knowledge_base

logger = logging.getLogger(__name__)

_agent_ready: bool = False
_agent_name_cache: Optional[str] = None
_project_client = None

AGENT_NAME = "rag-chat-agent"

AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that must use the knowledge base to answer all "
    "questions from the user. Do NOT answer from your own general knowledge — "
    "always call the knowledge base tool first. Every answer must include "
    "citations to the retrieved sources, rendered as "
    "\u3010message_idx:search_idx\u2020source_name\u3011. If the answer is not "
    "present in the knowledge base, respond with \"I don't know based on the "
    "workshop knowledge base.\""
)


def _get_credential():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if settings.azure_managed_identity_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_managed_identity_client_id)
    return DefaultAzureCredential()


def get_project_client():
    """Return AIProjectClient(allow_preview=True) — used by chat.py too."""
    global _project_client

    if not settings.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Azure AI services not configured. Set AZURE_AI_PROJECT_ENDPOINT.",
        )

    if _project_client is None:
        from azure.ai.projects import AIProjectClient

        _project_client = AIProjectClient(
            endpoint=settings.azure_ai_project_endpoint,
            credential=_get_credential(),
            allow_preview=True,
        )
    return _project_client


def get_agent_name() -> str:
    """Return the Foundry-portal agent name to pass in Responses.agent_reference."""
    return _agent_name_cache or AGENT_NAME


def create_or_get_agent() -> str:
    """Ensure the portal-registered agent version exists.

    Returns the agent name (used by chat.py in the Responses `agent_reference`).
    Idempotent.
    """
    global _agent_ready, _agent_name_cache

    if _agent_ready:
        return _agent_name_cache or AGENT_NAME

    from azure.ai.projects.models import MCPTool, PromptAgentDefinition

    refs = ensure_knowledge_base()
    mcp_tool = MCPTool(
        server_label="knowledge-base",
        server_url=refs.mcp_endpoint,
        project_connection_id=refs.project_connection_id,
        allowed_tools=["knowledge_base_retrieve"],
        require_approval="never",
    )
    definition = PromptAgentDefinition(
        model=settings.agent_model,
        instructions=AGENT_INSTRUCTIONS,
        tools=[mcp_tool],
    )

    try:
        agent_version = get_project_client().agents.create_version(
            AGENT_NAME,
            definition=definition,
            description="RAG chat agent — grounded via Foundry IQ Knowledge Base (MCP)",
        )
        logger.info(
            "Portal agent '%s' version %s registered (id=%s)",
            AGENT_NAME,
            getattr(agent_version, "version", "?"),
            getattr(agent_version, "id", "?"),
        )
    except Exception as exc:
        logger.error("Failed to register portal agent: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {exc}",
        ) from exc

    _agent_name_cache = AGENT_NAME
    _agent_ready = True
    return _agent_name_cache
