"""Foundry Agent Service — agent setup and lifecycle management.

The RAG agent uses a custom `search_documents` FunctionTool so that:
  1. The agent definition is visible in Azure AI Foundry portal as a
     NextGen "prompt" agent (not a legacy assistant).
  2. Any model that supports function calling (including gpt-4o-mini) works.
  3. The backend explicitly executes the AI Search query and returns the
     results to the agent, keeping the retrieval logic fully transparent.

Pattern follows the NextGen Foundry reference:
  - Connect via AIProjectClient (azure-ai-projects) using the project endpoint
    (https://{foundry}.services.ai.azure.com/api/projects/{project})
  - Create/reuse agent via project_client.agents — this maps directly to
    PromptAgentDefinition in the C# SDK and creates versioned prompt agents
    that are visible in the new Foundry portal with Type=prompt.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_project_client = None  # AIProjectClient — used for agent create/get/list (prompt-type)
_agents_client = None   # AgentsClient (azure-ai-agents) — used for threads/runs/messages

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
    """Return AIProjectClient.agents for agent create/get/list operations.

    AIProjectClient.agents (azure-ai-projects) creates agents via the NextGen
    Foundry project scope — equivalent to PromptAgentDefinition in C#.
    Agents created this way appear in the portal as Type=prompt with
    server-managed versioning, not as legacy assistants.

    NOTE: AgentsOperations from azure-ai-projects uses a flat API (no .threads,
    .messages, .runs sub-clients). Use get_agents_client() for runtime ops.
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

    azure-ai-agents AgentsClient exposes the nested sub-client API that
    chat.py relies on: .threads, .messages, .runs, etc.
    Uses the same project endpoint so it operates on the same agents.
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
    """Return the ID of the RAG agent, creating it if it doesn't exist yet.

    Follows the NextGen Foundry PromptAgentDefinition pattern:
    - Agents are created via AIProjectClient.agents (project-scoped endpoint)
    - A stable AGENT_NAME acts as the logical agent lineage identifier
    - Re-calling create_agent() with the same name creates a new managed version
    - Reusing an existing agent by name avoids accumulating duplicate versions

    If ``AGENT_ID`` is set in the environment, the agent is validated via the
    Foundry API before reuse. If it no longer exists or is a legacy assistant,
    we fall through to list/create so the agent is always a proper Foundry
    prompt agent visible in the portal with Type=prompt.
    """
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    # Use the project-scoped AIProjectClient.agents for create/get/list so that
    # the agent is created as a NextGen Foundry prompt agent (PromptAgentDefinition).
    project_agents = _get_project_agents()

    # Validate the persisted AGENT_ID against the Foundry project API before reusing
    if settings.agent_id:
        try:
            agent = project_agents.get_agent(settings.agent_id)
            _agent_id = agent.id
            logger.info("Reusing validated Foundry prompt agent: %s", _agent_id)
            return _agent_id
        except Exception as exc:
            logger.warning(
                "AGENT_ID '%s' not found in Foundry project — creating a new agent. (%s)",
                settings.agent_id, exc,
            )

    try:
        # Reuse existing agent version by stable name to avoid duplicate lineages.
        # In NextGen Foundry, agents with the same name share a version lineage —
        # listing by name and reusing is equivalent to "get latest version".
        for existing in project_agents.list_agents():
            if existing.name == AGENT_NAME:
                _agent_id = existing.id
                logger.info(
                    "Reusing existing Foundry prompt agent '%s': %s",
                    AGENT_NAME, _agent_id,
                )
                return _agent_id

        # Create a new prompt agent version under the stable logical name.
        # This maps to PromptAgentDefinition + CreateAgentVersionAsync in C#.
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
