"""Foundry Agent Service — agent setup and lifecycle management.

The RAG agent uses a custom `search_documents` FunctionTool so that:
  1. The agent definition is visible in Azure AI Foundry portal as a
     NextGen "prompt" agent (not a legacy assistant).
  2. Any model that supports function calling (including gpt-4o-mini) works.
  3. The backend explicitly executes the AI Search query and returns the
     results to the agent, keeping the retrieval logic fully transparent.

NextGen Foundry prompt-agent pattern (Python equivalent of C# PromptAgentDefinition):
  - Agent creation/lookup uses AIProjectClient.agents (azure-ai-projects).
    This calls POST {endpoint}/agents (not /assistants), so agents appear
    in the Foundry portal as Type=prompt with server-managed versioning.
  - Thread/run/message operations use standalone AgentsClient (azure-ai-agents).
    It exposes the nested sub-client API (.threads, .messages, .runs) that
    the chat router depends on, and the /threads path is the same regardless
    of which client created the agent.

Why two clients:
  - AgentsClient (azure-ai-agents) hits /assistants for agent CRUD → legacy portal
  - AIProjectClient.agents (azure-ai-projects) hits /agents for agent CRUD → new portal
  - Both hit the same /threads, /runs, /messages paths for runtime → compatible
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_project_client = None  # AIProjectClient — agent create/get via /agents endpoint
_agents_client = None   # AgentsClient (azure-ai-agents) — threads/runs/messages

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


def _get_project_agents():
    """Return AIProjectClient.agents for agent create/get via the /agents endpoint.

    Agents created here appear in the Foundry portal as Type=prompt.
    Only call create_agent() and get_agent() on the returned object —
    avoid list_agents() as method availability varies across SDK versions.
    """
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
        )
    return _project_client.agents


def get_agents_client():
    """Return the standalone AgentsClient for thread/run/message operations.

    azure-ai-agents AgentsClient provides the nested sub-client API
    (.threads, .messages, .runs) that chat.py relies on.
    The /threads and /runs paths are the same regardless of which client
    created the agent, so this works seamlessly with prompt agents created
    via AIProjectClient.agents.
    """
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
    """Return the ID of the RAG agent, creating it if needed.

    Uses AIProjectClient.agents (project-scoped /agents endpoint) so the agent
    is created as a NextGen Foundry prompt agent visible in the portal.

    Agent lifecycle:
      1. If AGENT_ID env var is set, validate it via get_agent() and reuse.
      2. If not found or invalid (e.g. legacy assistant ID), create a fresh one.
      3. The workflow persists the new AGENT_ID via az containerapp update so
         subsequent container restarts reuse the same agent version.
    """
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    project_agents = _get_project_agents()

    # Validate the persisted AGENT_ID before reusing.
    # get_agent() will raise if the ID doesn't exist in the /agents API,
    # which also rejects legacy /assistants-created IDs.
    if settings.agent_id:
        try:
            agent = project_agents.get_agent(settings.agent_id)
            _agent_id = agent.id
            logger.info("Reusing validated Foundry prompt agent: %s", _agent_id)
            return _agent_id
        except Exception as exc:
            logger.warning(
                "AGENT_ID '%s' invalid or not a Foundry prompt agent — creating new. (%s)",
                settings.agent_id, exc,
            )

    # Create a new prompt agent. With the project-scoped endpoint this calls
    # POST {endpoint}/agents, making it a NextGen Foundry prompt agent.
    # Equivalent to PromptAgentDefinition + CreateAgentVersionAsync in C#.
    try:
        agent = project_agents.create_agent(
            model=settings.agent_model,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            tools=[{"type": "function", "function": SEARCH_FUNCTION_SCHEMA}],
        )
        _agent_id = agent.id
        logger.info(
            "Created Foundry prompt agent '%s': %s (model=%s)",
            AGENT_NAME, _agent_id, settings.agent_model,
        )
        return _agent_id

    except Exception as exc:
        logger.error("Failed to create RAG agent: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {exc}",
        ) from exc
