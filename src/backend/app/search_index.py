"""Azure AI Search index creation and management."""

import logging

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from app.config import settings

logger = logging.getLogger(__name__)


def _build_index() -> SearchIndex:
    """Build the SearchIndex definition."""
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="default-vector-profile",
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            sortable=True,
        ),
        SimpleField(
            name="indexed_at",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="default-vectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=settings.azure_openai_endpoint,
                    deployment_name=settings.azure_openai_embedding_deployment,
                    model_name=settings.azure_openai_embedding_deployment,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-hnsw",
                vectorizer_name="default-vectorizer",
            )
        ],
    )

    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
        ),
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    return SearchIndex(
        name=settings.azure_search_index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def _get_index_client() -> SearchIndexClient:
    """Create a SearchIndexClient using managed identity when available."""
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if settings.azure_managed_identity_client_id:
        credential = ManagedIdentityCredential(
            client_id=settings.azure_managed_identity_client_id
        )
    else:
        credential = DefaultAzureCredential()

    return SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=credential,
    )


def create_or_update_index() -> None:
    """Create or update the search index (idempotent)."""
    client = _get_index_client()
    index = _build_index()
    result = client.create_or_update_index(index)
    logger.info("Search index '%s' created/updated successfully.", result.name)


def delete_index() -> None:
    """Delete the search index."""
    client = _get_index_client()
    client.delete_index(settings.azure_search_index_name)
    logger.info("Search index '%s' deleted.", settings.azure_search_index_name)
