"""Foundry Agent Service — agent setup and lifecycle management."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_agent_id: Optional[str] = None
_project_client = None

AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions based on the "
    "provided documents. Always cite your sources. If you don't know "
    "the answer, say so."
)


def get_project_client():
    """Return a cached AIProjectClient instance."""
    global _project_client

    if not settings.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Azure AI services not configured. Set AZURE_AI_PROJECT_ENDPOINT environment variable."
        )

    if _project_client is None:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

        if settings.azure_managed_identity_client_id:
            credential = ManagedIdentityCredential(
                client_id=settings.azure_managed_identity_client_id
            )
        else:
            credential = DefaultAzureCredential()

        _project_client = AIProjectClient(
            endpoint=settings.azure_ai_project_endpoint,
            credential=credential,
        )

    return _project_client


def create_or_get_agent() -> str:
    """Create (or reuse) the RAG agent and return its ID."""
    global _agent_id

    if _agent_id is not None:
        return _agent_id

    if settings.agent_id:
        _agent_id = settings.agent_id
        logger.info("Reusing existing agent: %s", _agent_id)
        return _agent_id

    client = get_project_client()

    try:
        from azure.ai.projects.models import (
            AzureAISearchTool,
            AzureAISearchToolResource,
            ConnectionType,
        )

        search_connection = client.connections.get_default(
            connection_type=ConnectionType.AZURE_AI_SEARCH,
            include_credentials=True,
        )

        search_tool = AzureAISearchTool()
        search_tool.add_index(
            AzureAISearchToolResource(
                index_connection_id=search_connection.id,
                index_name=settings.azure_search_index_name,
            )
        )

        agent = client.agents.create_agent(
            model=settings.agent_model,
            name="rag-chat-agent",
            instructions=AGENT_INSTRUCTIONS,
            tools=search_tool.definitions,
            tool_resources=search_tool.resources,
        )

        _agent_id = agent.id
        logger.info("Created agent: %s", _agent_id)
        return _agent_id

    except Exception as e:
        logger.error("Failed to create agent: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize AI agent: {str(e)}"
        )
