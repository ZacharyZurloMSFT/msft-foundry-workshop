"""Foundry IQ — register the AI Search index as a project-level Knowledge Source.

Instead of a `search_documents` function tool that the backend proxies, this
module registers the index as an `AzureAISearchIndex` **asset** on the Foundry
project. The asset then shows up under the portal's **Knowledge** tab and can be
attached to agents via `AzureAISearchTool` — the runtime performs retrieval
directly.

The two IDs the agent needs:

  * `project_connection_id` — the CognitiveSearch connection created by
    `ai-foundry.bicep` (`ai-search-connection`). Resolved via
    `AIProjectClient.connections.get(...)`.
  * `index_asset_id` — the Knowledge Source asset registered here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Name of the connection created by ai-foundry.bicep against the AI Search service.
SEARCH_CONNECTION_NAME = "ai-search-connection"

# Name / version of the Knowledge Source asset shown in the Foundry portal.
KNOWLEDGE_ASSET_NAME = "workshop-docs"
KNOWLEDGE_ASSET_VERSION = "1"


@dataclass
class KnowledgeRefs:
    """The two IDs an agent needs to reference the AI Search knowledge source."""

    project_connection_id: str
    index_asset_id: str
    index_name: str


_cache: Optional[KnowledgeRefs] = None


def _get_credential():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if settings.azure_managed_identity_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_managed_identity_client_id)
    return DefaultAzureCredential()


def _get_project_client():
    from azure.ai.projects import AIProjectClient

    return AIProjectClient(
        endpoint=settings.azure_ai_project_endpoint,
        credential=_get_credential(),
        allow_preview=True,
    )


def ensure_search_knowledge_source() -> KnowledgeRefs:
    """Register (or refresh) the AI Search index as a Foundry Knowledge Source.

    Idempotent — safe to call on every startup. Returns the connection and asset
    IDs needed to attach the knowledge source to an agent.
    """
    global _cache
    if _cache is not None:
        return _cache

    from azure.ai.projects.models import AzureAISearchIndex, FieldMapping

    client = _get_project_client()

    # Resolve the AI Search connection's fully-qualified project ID.
    conn = client.connections.get(SEARCH_CONNECTION_NAME)
    project_connection_id = getattr(conn, "id", None) or conn.get("id")
    if not project_connection_id:
        raise RuntimeError(
            f"Could not resolve connection '{SEARCH_CONNECTION_NAME}' — is the "
            "Bicep-provisioned ai-search-connection present on the Foundry account?"
        )
    logger.info("Resolved AI Search connection: %s", project_connection_id)

    # Register the index as a Knowledge asset. Field mapping tells Foundry IQ
    # which fields carry the text, title, url, and vector so citations render
    # nicely in the portal + API responses.
    field_mapping = FieldMapping(
        content_fields=["content"],
        title_field="title",
        url_field="source",
        vector_fields=["content_vector"],
    )
    index_asset = AzureAISearchIndex(
        name=KNOWLEDGE_ASSET_NAME,
        version=KNOWLEDGE_ASSET_VERSION,
        connection_name=SEARCH_CONNECTION_NAME,
        index_name=settings.azure_search_index_name,
        field_mapping=field_mapping,
        description="Workshop RAG documents (Azure AI Search)",
    )

    result = client.indexes.create_or_update(
        name=KNOWLEDGE_ASSET_NAME,
        version=KNOWLEDGE_ASSET_VERSION,
        index=index_asset,
    )
    index_asset_id = getattr(result, "id", None) or ""
    logger.info(
        "Registered Foundry Knowledge Source '%s' v%s → asset id=%s (index=%s)",
        KNOWLEDGE_ASSET_NAME,
        KNOWLEDGE_ASSET_VERSION,
        index_asset_id or "<unknown>",
        settings.azure_search_index_name,
    )

    _cache = KnowledgeRefs(
        project_connection_id=project_connection_id,
        index_asset_id=index_asset_id,
        index_name=settings.azure_search_index_name,
    )
    return _cache


def get_cached_refs() -> Optional[KnowledgeRefs]:
    """Return cached refs without triggering a network call. None if not registered yet."""
    return _cache
