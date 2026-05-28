"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables."""

    # Azure AI Project (Foundry)
    azure_ai_project_endpoint: str = ""
    azure_managed_identity_client_id: str = ""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_index_name: str = "documents"

    # Agent
    agent_model: str = "gpt-4o-mini"
    agent_id: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def is_configured(self) -> bool:
        """Check if the minimum required Azure config is set."""
        return bool(self.azure_ai_project_endpoint)


settings = Settings()
