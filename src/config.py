"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")

    # LLM Provider (Phase 3)
    llm_provider: Literal["openai", "ollama"] = Field(
        default="openai",
        validation_alias="LLM_PROVIDER"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="llama3.2",
        validation_alias="OLLAMA_MODEL"
    )

    # Embedding Model
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL"
    )

    # Storage - Phase 1 (JSON)
    memory_file: str = Field(
        default="data/memory.json",
        validation_alias="MEMORY_FILE"
    )

    # Storage - Phase 2 (SQLite)
    storage_backend: Literal["json", "sqlite"] = Field(
        default="json",
        validation_alias="STORAGE_BACKEND"
    )
    database_path: str = Field(
        default="data/memory.db",
        validation_alias="DATABASE_PATH"
    )

    # Retrieval Settings
    retrieval_top_k: int = Field(
        default=10,
        validation_alias="RETRIEVAL_TOP_K"
    )
    similarity_threshold: float = Field(
        default=0.7,
        validation_alias="SIMILARITY_THRESHOLD"
    )
    duplicate_threshold: float = Field(
        default=0.85,
        validation_alias="DUPLICATE_THRESHOLD"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL"
    )

    # Streamlit
    streamlit_port: int = Field(
        default=8501,
        validation_alias="STREAMLIT_PORT"
    )

    # Consolidation Settings (Phase 3)
    consolidation_enabled: bool = Field(
        default=True,
        validation_alias="CONSOLIDATION_ENABLED"
    )
    duplicate_merge_threshold: float = Field(
        default=0.9,
        validation_alias="DUPLICATE_MERGE_THRESHOLD"
    )
    prune_inactive_days: int = Field(
        default=30,
        validation_alias="PRUNE_INACTIVE_DAYS"
    )
    prune_importance_threshold: float = Field(
        default=0.3,
        validation_alias="PRUNE_IMPORTANCE_THRESHOLD"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance - lazy loaded
_settings: Optional[Settings] = None


def settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
