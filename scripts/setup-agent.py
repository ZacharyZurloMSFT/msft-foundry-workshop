#!/usr/bin/env python3
"""
Foundry Agent Setup Script

Creates a RAG agent in the Azure AI Foundry project with a `search_documents`
function tool.  The agent will appear in the Foundry portal under the project's
Agents section.  The backend calls this agent at runtime and handles the
search_documents tool call by executing a real Azure AI Search query.

Usage:
    python scripts/setup-agent.py

Required environment variables:
    AZURE_AI_PROJECT_ENDPOINT  - Foundry project endpoint
                                 (https://<name>.services.ai.azure.com/api/projects/<project>)

Optional:
    AZURE_OPENAI_CHAT_DEPLOYMENT      - Model to use (default: gpt-4o-mini)
    AZURE_SEARCH_INDEX_NAME           - Search index name (default: documents)
    AZURE_MANAGED_IDENTITY_CLIENT_ID  - User-assigned managed identity client ID
"""

import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

AGENT_NAME = "rag-chat-agent"

AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions based on the knowledge base. "
    "ALWAYS call the search_documents tool before answering to find relevant content. "
    "Cite your sources by mentioning the document title or filename. "
    "If the answer is not found in the search results, say so clearly."
)

# Function tool schema — the backend backend handles the actual AI Search call
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


def get_credential():
    """Return a credential, preferring managed identity when configured."""
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    client_id = os.environ.get("AZURE_MANAGED_IDENTITY_CLIENT_ID", "")
    if client_id:
        logger.info("Using ManagedIdentityCredential (client_id=%s...)", client_id[:8])
        return ManagedIdentityCredential(client_id=client_id)
    logger.info("Using DefaultAzureCredential")
    return DefaultAzureCredential()


def create_agent(endpoint: str, credential) -> str:
    """Create the RAG agent in Foundry and return its ID."""
    model = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    search_index = os.environ.get("AZURE_SEARCH_INDEX_NAME", "documents")

    logger.info("Creating RAG agent (model=%s, index=%s)", model, search_index)

    from azure.ai.agents import AgentsClient

    agents_client = AgentsClient(endpoint=endpoint, credential=credential)

    # List existing agents and reuse if one already exists with the same name
    for existing in agents_client.list_agents():
        if existing.name == AGENT_NAME:
            logger.info("Agent '%s' already exists: %s — deleting and recreating", AGENT_NAME, existing.id)
            agents_client.delete_agent(existing.id)
            break

    agent = agents_client.create_agent(
        model=model,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=[{"type": "function", "function": SEARCH_FUNCTION_SCHEMA}],
    )

    logger.info("✅ Agent created: %s", agent.id)
    return agent.id


def save_agent_id(agent_id: str) -> None:
    """Persist the agent ID so the workflow can set it as an env var."""
    config = {"agent_id": agent_id}
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "backend", ".agent-config.json"
    )
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.info("Agent ID saved to %s", config_path)
    logger.info("")
    logger.info("Set on the backend container app with:")
    logger.info("  az containerapp update --name <app> --resource-group <rg> \\")
    logger.info('    --set-env-vars "AGENT_ID=%s"', agent_id)


def main() -> None:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
    if not endpoint:
        logger.error("AZURE_AI_PROJECT_ENDPOINT is not set.")
        sys.exit(1)

    logger.info("Foundry Project: %s", endpoint)
    logger.info("")

    credential = get_credential()

    logger.info("=" * 50)
    logger.info("Creating RAG agent with search_documents tool")
    logger.info("=" * 50)
    agent_id = create_agent(endpoint, credential)

    logger.info("")
    logger.info("=" * 50)
    logger.info("Saving configuration")
    logger.info("=" * 50)
    save_agent_id(agent_id)

    logger.info("")
    logger.info("🎉 Agent setup complete!")


if __name__ == "__main__":
    main()
