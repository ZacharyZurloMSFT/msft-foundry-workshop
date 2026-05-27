"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables."""

    # Azure AI Project (Foundry)
    azure_ai_project_endpoint: str = ""
    azure_managed_identity_client_id: str = ""
    azure_ai_project_connection_string: str = ""
    
    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-5-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    
    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_index_name: str = "documents"
    azure_ai_search_index_name: str = "documents"
    azure_ai_search_connection_name: str = ""
    
    # Agent
    agent_model: str = "gpt-5-mini"
    agent_id: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def is_configured(self) -> bool:
        """Check if the minimum required Azure config is set."""
        return bool(self.azure_ai_project_endpoint or self.azure_ai_project_connection_string)


settings = Settings()
