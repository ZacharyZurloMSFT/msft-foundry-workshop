"""Foundry Agent Service — agent setup and lifecycle management.

The RAG agent is grounded by a **Foundry IQ knowledge source** — an
`AzureAISearchTool` bound to the workshop's AI Search index — instead of a
custom `search_documents` FunctionTool. Retrieval happens inside the runtime,
so the backend does not receive `requires_action` events for search.

Two-client design (azure-ai-projects 2.x + azure-ai-agents 1.x):

  Portal registration (azure-ai-projects AgentsOperations):
    - AIProjectClient(allow_preview=True).agents.create_version(agent_name,
        definition=PromptAgentDefinition(tools=[AzureAISearchTool(...)]))
    - Shows in the Foundry portal as Type=prompt with a Knowledge source
    - Idempotent: create_version bumps the version if the tool changes
    - Non-fatal: portal registration failure never breaks chat

  Runtime (azure-ai-agents AgentsClient):
    - agents_client.create_agent(model, name, instructions,
        tools=tool.definitions, tool_resources=tool.resources)
    - .threads / .runs / .messages used by chat.py

Stale-tool refresh:
  If AGENT_ID points at an agent still using the legacy `function`-typed
  `search_documents` tool, `_needs_refresh()` detects that and recreates the
  runtime agent with the new `azure_ai_search` tool.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings
from app.knowledge import ensure_search_knowledge_source

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_project_client = None  # AIProjectClient (azure-ai-projects) — portal registration
_agents_client = None   # AgentsClient (azure-ai-agents) — runtime threads/runs/messages

AGENT_NAME = "rag-chat-agent"

AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions grounded in the workshop "
    "knowledge base. Use the retrieved passages to compose your answer and cite "
    "the source document by its title or filename for every fact. If the answer "
    "is not present in the knowledge base, say so clearly."
)


def _get_credential():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if settings.azure_managed_identity_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_managed_identity_client_id)
    return DefaultAzureCredential()


def _get_project_client():
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
    """Return the standalone AgentsClient for thread/run/message operations."""
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


def _build_runtime_search_tool():
    """Build the AgentsClient-flavoured AzureAISearchTool bound to the workshop index."""
    from azure.ai.agents.models import AzureAISearchTool, AzureAISearchQueryType

    refs = ensure_search_knowledge_source()
    return AzureAISearchTool(
        index_connection_id=refs.project_connection_id,
        index_name=refs.index_name,
        query_type=AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
        top_k=5,
        index_asset_id=refs.index_asset_id or "",
    )


def _needs_refresh(agent) -> bool:
    """True if the persisted agent is still on the legacy function tool."""
    try:
        for tool in getattr(agent, "tools", []) or []:
            t_type = getattr(tool, "type", None) or (isinstance(tool, dict) and tool.get("type"))
            if t_type == "azure_ai_search":
                return False
        return True
    except Exception:
        return True


def _ensure_portal_agent(search_tool) -> None:
    """Register/update the RAG agent in the Foundry portal (Type=prompt)."""
    try:
        project_client = _get_project_client()
        project_agents = project_client.agents

        from azure.ai.projects.models import (
            AISearchIndexResource,
            AzureAISearchQueryType,
            AzureAISearchTool as ProjectAISearchTool,
            AzureAISearchToolResource,
            PromptAgentDefinition,
        )

        refs = ensure_search_knowledge_source()
        portal_tool = ProjectAISearchTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=refs.project_connection_id,
                        index_name=refs.index_name,
                        query_type=AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
                        top_k=5,
                        index_asset_id=refs.index_asset_id or "",
                    )
                ]
            )
        )

        definition = PromptAgentDefinition(
            model=settings.agent_model,
            instructions=AGENT_INSTRUCTIONS,
            tools=[portal_tool],
        )

        agent_version = project_agents.create_version(
            AGENT_NAME,
            definition=definition,
            description="RAG chat agent — grounded via Foundry IQ + AI Search knowledge source",
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


def _create_runtime_agent(search_tool):
    """Create a fresh runtime agent bound to the knowledge source."""
    agents_client = get_agents_client()
    agent = agents_client.create_agent(
        model=settings.agent_model,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=search_tool.definitions,
        tool_resources=search_tool.resources,
    )
    logger.info(
        "Created runtime agent '%s': %s (model=%s, knowledge=AI Search)",
        AGENT_NAME, agent.id, settings.agent_model,
    )
    return agent


def create_or_get_agent() -> str:
    """Return the ID of the RAG runtime agent, creating (or refreshing) it as needed."""
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    agents_client = get_agents_client()
    search_tool = _build_runtime_search_tool()

    # Validate the persisted AGENT_ID before reusing.
    if settings.agent_id:
        try:
            agent = agents_client.get_agent(settings.agent_id)
            if _needs_refresh(agent):
                logger.info(
                    "Runtime agent %s uses a legacy tool — deleting and recreating "
                    "with the AI Search knowledge source.", settings.agent_id,
                )
                try:
                    agents_client.delete_agent(settings.agent_id)
                except Exception as exc:
                    logger.warning("Delete of stale agent failed (continuing): %s", exc)
                agent = _create_runtime_agent(search_tool)
            else:
                logger.info("Reusing runtime agent: %s", agent.id)
            _agent_id = agent.id
            _ensure_portal_agent(search_tool)
            return _agent_id
        except Exception as exc:
            logger.warning(
                "AGENT_ID '%s' invalid — creating new runtime agent. (%s)",
                settings.agent_id, exc,
            )

    try:
        agent = _create_runtime_agent(search_tool)
        _agent_id = agent.id
    except Exception as exc:
        logger.error("Failed to create runtime agent: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {exc}",
        ) from exc

    _ensure_portal_agent(search_tool)
    return _agent_id
