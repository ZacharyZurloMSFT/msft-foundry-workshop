"""Foundry IQ Knowledge Base + RemoteTool project connection.

The New Foundry portal's Knowledge tab expects a first-class **Knowledge Base**
that lives on the Azure AI Search service (preview API 2026-05-01-preview) and
exposes an MCP endpoint. Agents attach it via a `RemoteTool` project connection
+ `MCPTool` — that's what places the KB under Knowledge on the agent card
(instead of showing up as a plain `Azure AI Search` tool).

This module is idempotent — every backend startup:

  1. PUTs the KB (`workshop-kb`) on AI Search, referencing our `documents`
     search index as a `searchIndex` knowledge source.
  2. PUTs a `RemoteTool` project connection (`workshop-kb-conn`) via ARM
     targeting the KB's MCP endpoint, authenticated with the project's
     ProjectManagedIdentity.

Both calls are safe to repeat; PUT semantics create-or-update.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, get_bearer_token_provider

from app.config import settings

logger = logging.getLogger(__name__)

KB_NAME = "workshop-kb"
KS_NAME = "workshop-docs-source"
KB_API_VERSION = "2026-05-01-preview"
CONNECTION_NAME = "workshop-kb-conn"
CONN_API_VERSION = "2025-10-01-preview"

# Optional pin: if this env var is present, we assume the KB has already been
# created and just resolve the MCP endpoint / connection ID from state.
KB_ENDPOINT_ENV = "FOUNDRY_KB_MCP_ENDPOINT"


@dataclass
class KnowledgeBaseRefs:
    """Everything the agent needs to attach the KB via MCPTool."""

    mcp_endpoint: str
    project_connection_id: str
    project_connection_name: str


_cache: Optional[KnowledgeBaseRefs] = None


def _get_credential():
    if settings.azure_managed_identity_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_managed_identity_client_id)
    return DefaultAzureCredential()


# ---------------------------------------------------------------------------
# Project resource-ID resolution
# ---------------------------------------------------------------------------

def _resolve_project_resource_id() -> str:
    """Build the ARM resource ID for the Foundry project.

    The project endpoint looks like:
      https://<foundry>.services.ai.azure.com/api/projects/<project>

    Combined with subscriptionId + resourceGroup env vars (populated by Bicep
    on the container app) or by parsing az/env, we can compose:
      /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry>/projects/<project>
    """
    endpoint = settings.azure_ai_project_endpoint
    m = re.match(r"https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/?]+)", endpoint)
    if not m:
        raise RuntimeError(f"Cannot parse Foundry project endpoint: {endpoint}")
    foundry_name, project_name = m.group(1), m.group(2)

    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP", "")
    if not subscription_id or not resource_group:
        raise RuntimeError(
            "AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP must be set on the "
            "backend container app to build the Foundry project resource ID."
        )

    return (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{foundry_name}"
        f"/projects/{project_name}"
    )


def _search_service_endpoint() -> str:
    endpoint = settings.azure_search_endpoint
    return endpoint.rstrip("/")


# ---------------------------------------------------------------------------
# Knowledge Base creation on Azure AI Search
# ---------------------------------------------------------------------------

def _ensure_kb_on_search(credential) -> str:
    """PUT the knowledge source + knowledge base on AI Search.

    Returns the MCP endpoint URL that agents call to hit the KB.
    """
    search_endpoint = _search_service_endpoint()
    token_provider = get_bearer_token_provider(credential, "https://search.azure.com/.default")

    headers = {
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json",
    }

    # ---- 1. Create the knowledge SOURCE — points at our AI Search index ----
    ks_url = f"{search_endpoint}/knowledgesources/{KS_NAME}?api-version={KB_API_VERSION}"
    ks_payload = {
        "name": KS_NAME,
        "kind": "searchIndex",
        "description": "Workshop documents (Azure AI Search index)",
        "searchIndexParameters": {
            "searchIndexName": settings.azure_search_index_name,
            "semanticConfigurationName": "default-semantic-config",
            "sourceDataFields": [
                {"name": "title"},
                {"name": "source"},
                {"name": "content"},
            ],
        },
    }
    r = requests.put(ks_url, headers=headers, json=ks_payload, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Knowledge source PUT failed ({r.status_code}): {r.text}")
    logger.info("Knowledge source '%s' PUT succeeded (status=%s)", KS_NAME, r.status_code)

    # ---- 2. Create the knowledge BASE — references the source by name ----
    kb_url = f"{search_endpoint}/knowledgebases/{KB_NAME}?api-version={KB_API_VERSION}"
    kb_payload = {
        "name": KB_NAME,
        "description": "Workshop RAG knowledge base — orchestrates retrieval over the documents index",
        "knowledgeSources": [
            {"name": KS_NAME}
        ],
        # "minimal" reasoning means the KB does not need an LLM for query planning.
        # Any higher effort ("low"/"medium"/"high") requires a model in `models`.
        "retrievalReasoningEffort": {"kind": "minimal"},
    }
    r = requests.put(kb_url, headers=headers, json=kb_payload, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"KB PUT failed ({r.status_code}): {r.text}")
    logger.info("KB '%s' PUT succeeded on %s (status=%s)", KB_NAME, search_endpoint, r.status_code)

    mcp_endpoint = f"{search_endpoint}/knowledgebases/{KB_NAME}/mcp?api-version={KB_API_VERSION}"
    return mcp_endpoint


# ---------------------------------------------------------------------------
# RemoteTool connection on the Foundry project (ARM)
# ---------------------------------------------------------------------------

def _ensure_project_connection(credential, mcp_endpoint: str) -> str:
    """PUT a RemoteTool connection on the Foundry project. Returns its ARM ID."""
    project_resource_id = _resolve_project_resource_id()
    conn_url = (
        f"https://management.azure.com{project_resource_id}"
        f"/connections/{CONNECTION_NAME}?api-version={CONN_API_VERSION}"
    )

    token_provider = get_bearer_token_provider(credential, "https://management.azure.com/.default")
    headers = {
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json",
    }

    body = {
        "name": CONNECTION_NAME,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": mcp_endpoint,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"},
        },
    }
    r = requests.put(conn_url, headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Connection PUT failed ({r.status_code}): {r.text}")
    conn = r.json()
    conn_id = conn.get("id") or conn.get("properties", {}).get("id") or ""
    logger.info("Project connection '%s' PUT succeeded (id=%s)", CONNECTION_NAME, conn_id)
    return conn_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_knowledge_base() -> KnowledgeBaseRefs:
    """Create-or-update the Foundry IQ KB + RemoteTool connection.

    Idempotent. Safe to call on every startup. Returns everything the agent
    needs to attach the KB via MCPTool.
    """
    global _cache
    if _cache is not None:
        return _cache

    credential = _get_credential()

    mcp_endpoint = _ensure_kb_on_search(credential)
    conn_id = _ensure_project_connection(credential, mcp_endpoint)

    _cache = KnowledgeBaseRefs(
        mcp_endpoint=mcp_endpoint,
        project_connection_id=conn_id or CONNECTION_NAME,
        project_connection_name=CONNECTION_NAME,
    )
    return _cache


def get_cached_refs() -> Optional[KnowledgeBaseRefs]:
    return _cache
