#!/usr/bin/env python3
"""
Foundry Agent Setup Script

Creates connections and a RAG agent in the Azure AI Foundry project.
Run this AFTER infrastructure is deployed and BEFORE using the app.

Usage:
    python scripts/setup-agent.py

Required environment variables:
    AZURE_AI_PROJECT_ENDPOINT  - Foundry project endpoint (.services.ai.azure.com)
    AZURE_SEARCH_ENDPOINT      - AI Search endpoint
    AZURE_SEARCH_INDEX_NAME    - Search index name (default: documents)
    AZURE_OPENAI_ENDPOINT      - OpenAI endpoint (optional, for connection setup)

Optional:
    AZURE_MANAGED_IDENTITY_CLIENT_ID - User-assigned managed identity client ID
"""

import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_credential():
    """Get Azure credential, preferring managed identity if configured."""
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    client_id = os.environ.get("AZURE_MANAGED_IDENTITY_CLIENT_ID", "")
    if client_id:
        logger.info(f"Using ManagedIdentityCredential (client_id={client_id[:8]}...)")
        return ManagedIdentityCredential(client_id=client_id)
    else:
        logger.info("Using DefaultAzureCredential")
        return DefaultAzureCredential()


def create_agent(project_client) -> str:
    """Create the RAG agent with AI Search grounding tool."""
    search_index = os.environ.get("AZURE_SEARCH_INDEX_NAME", "documents")
    model = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5-mini")

    logger.info(f"Creating RAG agent with model={model}, index={search_index}")

    try:
        from azure.ai.projects.models import (
            AzureAISearchTool,
            AzureAISearchToolResource,
            ConnectionType,
        )

        # Get the default AI Search connection
        search_connection = project_client.connections.get_default(
            connection_type=ConnectionType.AZURE_AI_SEARCH,
            include_credentials=True,
        )
        logger.info(f"Using search connection: {search_connection.id}")

        # Configure search tool
        search_tool = AzureAISearchTool()
        search_tool.add_index(
            AzureAISearchToolResource(
                index_connection_id=search_connection.id,
                index_name=search_index,
            )
        )

        # Create the agent
        agent = project_client.agents.create_agent(
            model=model,
            name="rag-chat-agent",
            instructions=(
                "You are a helpful assistant that answers questions based on the "
                "provided documents. Always cite your sources with specific quotes "
                "or references. If the answer is not in the documents, say so clearly."
            ),
            tools=search_tool.definitions,
            tool_resources=search_tool.resources,
        )

        logger.info(f"✅ Agent created: {agent.id}")
        return agent.id

    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        logger.info("")
        logger.info("Common fixes:")
        logger.info("1. Ensure AI Search connection exists in the Foundry project")
        logger.info("   → Go to ai.azure.com → project → Management → Connected resources")
        logger.info("2. Ensure the search index exists (run: python scripts/setup-index.py)")
        logger.info("3. Ensure the managed identity has the required RBAC roles")
        raise


def save_agent_id(agent_id: str):
    """Save agent ID for the backend to use."""
    config = {"agent_id": agent_id}
    config_path = os.path.join(os.path.dirname(__file__), "..", "src", "backend", ".agent-config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Agent ID saved to {config_path}")
    logger.info("")
    logger.info("To use this agent, set the environment variable:")
    logger.info(f"  AGENT_ID={agent_id}")
    logger.info("")
    logger.info("Or update the backend container app:")
    logger.info(f'  az containerapp update --name <backend-app> --resource-group <rg> --set-env-vars "AGENT_ID={agent_id}"')


def main():
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
    if not endpoint:
        logger.error("AZURE_AI_PROJECT_ENDPOINT is not set!")
        logger.info("Set it to your Foundry project's .services.ai.azure.com endpoint")
        sys.exit(1)

    logger.info(f"Foundry Project: {endpoint}")
    logger.info("")

    # Initialize client
    from azure.ai.projects import AIProjectClient
    credential = get_credential()
    client = AIProjectClient(endpoint=endpoint, credential=credential)

    # Create agent (connections are created in Bicep)
    logger.info("=" * 50)
    logger.info("Creating RAG agent")
    logger.info("=" * 50)
    agent_id = create_agent(client)

    # Step 3: Save config
    logger.info("")
    logger.info("=" * 50)
    logger.info("Step 3: Saving configuration")
    logger.info("=" * 50)
    save_agent_id(agent_id)

    logger.info("")
    logger.info("🎉 Setup complete!")


if __name__ == "__main__":
    main()
