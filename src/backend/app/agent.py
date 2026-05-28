"""Foundry Agent Service — agent setup and lifecycle management.

The RAG agent uses a custom `search_documents` FunctionTool so that:
  1. The agent definition is visible in Azure AI Foundry portal.
  2. Any model that supports function calling (including gpt-4o-mini) works.
  3. The backend explicitly executes the AI Search query and returns the
     results to the agent, keeping the retrieval logic fully transparent.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_agents_client = None

AGENT_NAME = "rag-chat-agent"

AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions based on the knowledge base. "
    "ALWAYS call the search_documents tool before answering to find relevant content. "
    "Cite your sources by mentioning the document title or filename. "
    "If the answer is not found in the search results, say so clearly."
)

# Function tool schema — the backend executes the actual AI Search query
SEARCH_FUNCTION_SCHEMA = {
    "name": "search_documents",
    "description": (
        "Search the knowledge base for relevant information. "
        "Call this tool with a natural language query to retrieve content "
        "from the indexed documents before composing your answer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A natural language search query to find relevant documents.",
            }
        },
        "required": ["query"],
    },
}


def _get_credential():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if settings.azure_managed_identity_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_managed_identity_client_id)
    return DefaultAzureCredential()


def get_agents_client():
    """Return a cached AgentsClient instance."""
    global _agents_client

    if not settings.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Azure AI services not configured. Set AZURE_AI_PROJECT_ENDPOINT.",
        )

    if _agents_client is None:
        from azure.ai.agents import AgentsClient

        _agents_client = AgentsClient(
            endpoint=settings.azure_ai_project_endpoint,
            credential=_get_credential(),
        )

    return _agents_client


def create_or_get_agent() -> str:
    """Return the ID of the RAG agent, creating it if it doesn't exist yet.

    If ``AGENT_ID`` is set in the environment (by the deployment workflow
    after running setup-agent.py), the pre-created agent is reused.
    Otherwise, a new agent is created at runtime.
    """
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    # Prefer the agent created by the deployment script
    if settings.agent_id:
        _agent_id = settings.agent_id
        logger.info("Reusing pre-created agent: %s", _agent_id)
        return _agent_id

    agents_client = get_agents_client()

    try:
        agent = agents_client.create_agent(
            model=settings.agent_model,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            tools=[{"type": "function", "function": SEARCH_FUNCTION_SCHEMA}],
        )
        _agent_id = agent.id
        logger.info("Created RAG agent: %s (model=%s)", _agent_id, settings.agent_model)
        return _agent_id

    except Exception as exc:
        logger.error("Failed to create RAG agent: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {exc}",
        ) from exc
