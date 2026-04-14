"""Azure client initialization."""

import logging

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from app.config import settings

logger = logging.getLogger(__name__)

credential = DefaultAzureCredential()


def get_project_client() -> AIProjectClient | None:
    """Return an AIProjectClient if the endpoint is configured."""
    if not settings.azure_ai_project_endpoint:
        logger.warning("AZURE_AI_PROJECT_ENDPOINT not set — skipping project client init")
        return None
    return AIProjectClient(
        endpoint=settings.azure_ai_project_endpoint,
        credential=credential,
    )


def get_search_client() -> SearchClient | None:
    """Return a SearchClient if the endpoint is configured."""
    if not settings.azure_search_endpoint:
        logger.warning("AZURE_SEARCH_ENDPOINT not set — skipping search client init")
        return None
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=credential,
    )
