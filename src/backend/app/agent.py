"""Foundry Agent Service — agent setup and lifecycle management.

The RAG agent uses a custom ``search_documents`` FunctionTool so that:
  1. The agent definition is visible in Azure AI Foundry portal as a
     NextGen "prompt" agent (not a legacy assistant).
  2. Any model that supports function calling (including gpt-4o-mini) works.
  3. The backend explicitly executes the AI Search query and returns the
     results to the agent, keeping the retrieval logic fully transparent.

Two-client design (azure-ai-projects 2.x + azure-ai-agents 1.x):

  Portal registration (azure-ai-projects AgentsOperations):
    - AIProjectClient(allow_preview=True).agents.create_version(agent_name, definition=PromptAgentDefinition(...))
    - Calls POST {endpoint}/agents/{name}/versions → shows as Type=prompt in Foundry portal
    - Idempotent: checks agents.get(agent_name) before creating a new version
    - Non-fatal: portal registration failure never breaks chat

  Runtime (azure-ai-agents AgentsClient mixin methods + sub-clients):
    - agents_client.create_agent(model, name, instructions, tools) → asst_xxx ID via /assistants
    - agents_client.get_agent(id) → validates the persisted AGENT_ID
    - agents_client.threads.*, .runs.*, .messages.* → used by chat.py

Why two clients:
  - AgentsClient(/assistants) provides the threads/runs nested sub-client API chat.py needs
  - AIProjectClient(/agents/{name}/versions) makes the agent appear in the NextGen Foundry portal
  - Both use the same project endpoint and managed-identity credential
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_project_client = None  # AIProjectClient (azure-ai-projects) — portal registration
_agents_client = None   # AgentsClient (azure-ai-agents) — runtime threads/runs/messages

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
        "Call this tool with a natural language search query to retrieve content "
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


def _get_project_client():
    """Return AIProjectClient (allow_preview=True) for portal registration.

    allow_preview=True enables the Foundry-Features header required for
    PromptAgentDefinition to be accepted by the /agents API.
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
            allow_preview=True,
        )
    return _project_client


def get_agents_client():
    """Return the standalone AgentsClient for thread/run/message operations.

    azure-ai-agents AgentsClient provides:
    - Top-level mixin: create_agent(), get_agent() via /assistants path
    - Nested sub-clients: .threads, .messages, .runs used by chat.py
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


def _ensure_portal_agent() -> None:
    """Register the RAG agent in the Foundry portal as Type=prompt.

    Uses the azure-ai-projects 2.x API:
      - agents.get(agent_name)          → check if already registered
      - agents.create_version(name, ...) → register with PromptAgentDefinition

    This is non-fatal: portal registration failure never breaks chat functionality.
    Idempotent: skips create_version if the portal agent already exists.
    """
    try:
        project_client = _get_project_client()
        project_agents = project_client.agents

        # Check whether the portal agent already exists under this name.
        try:
            existing = project_agents.get(AGENT_NAME)
            logger.info(
                "Portal agent '%s' already registered in Foundry (latest version: %s)",
                AGENT_NAME, getattr(existing, "latest_version", "unknown"),
            )
            return
        except Exception:
            pass  # 404 or other error → agent not yet registered

        # Build the PromptAgentDefinition (equivalent to C# PromptAgentDefinition)
        from azure.ai.projects.models import FunctionTool, PromptAgentDefinition

        function_tool = FunctionTool(
            name=SEARCH_FUNCTION_SCHEMA["name"],
            description=SEARCH_FUNCTION_SCHEMA["description"],
            parameters=SEARCH_FUNCTION_SCHEMA["parameters"],
            strict=False,
        )

        definition = PromptAgentDefinition(
            model=settings.agent_model,
            instructions=AGENT_INSTRUCTIONS,
            tools=[function_tool],
        )

        # Create a new agent version — equivalent to CreateAgentVersionAsync in C#
        agent_version = project_agents.create_version(
            AGENT_NAME,
            definition=definition,
            description="RAG chat agent for the Foundry workshop",
        )
        logger.info(
            "Registered Foundry portal agent '%s' version %s (id=%s)",
            AGENT_NAME,
            getattr(agent_version, "version", "?"),
            getattr(agent_version, "id", "?"),
        )

    except Exception as exc:
        logger.warning(
            "Portal agent registration failed (non-fatal — chat will still work): %s", exc
        )


def create_or_get_agent() -> str:
    """Return the ID of the RAG runtime agent, creating it if needed.

    Runtime agent lifecycle (uses AgentsClient / /assistants path):
      1. If AGENT_ID env var is set, validate via get_agent() and reuse.
      2. If not found or invalid, create a fresh runtime agent.
      3. Portal registration via _ensure_portal_agent() runs after the runtime
         agent is ready — this is what makes the agent visible in the Foundry portal.

    The AGENT_ID persisted by the workflow is always the runtime agent ID (asst_xxx)
    since that is what chat.py passes to threads.runs.create(assistant_id=...).
    """
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    agents_client = get_agents_client()

    # Validate the persisted AGENT_ID before reusing.
    if settings.agent_id:
        try:
            agent = agents_client.get_agent(settings.agent_id)
            _agent_id = agent.id
            logger.info("Reusing validated runtime agent: %s", _agent_id)
            _ensure_portal_agent()
            return _agent_id
        except Exception as exc:
            logger.warning(
                "AGENT_ID '%s' invalid — creating new runtime agent. (%s)",
                settings.agent_id, exc,
            )

    # Create a new runtime agent via AgentsClient (calls /assistants).
    # This provides the asst_xxx ID that threads/runs/messages use.
    try:
        agent = agents_client.create_agent(
            model=settings.agent_model,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            tools=[{"type": "function", "function": SEARCH_FUNCTION_SCHEMA}],
        )
        _agent_id = agent.id
        logger.info(
            "Created runtime agent '%s': %s (model=%s)",
            AGENT_NAME, _agent_id, settings.agent_model,
        )
    except Exception as exc:
        logger.error("Failed to create runtime agent: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {exc}",
        ) from exc

    # Register in Foundry portal as Type=prompt (non-fatal if fails).
    _ensure_portal_agent()

    return _agent_id
