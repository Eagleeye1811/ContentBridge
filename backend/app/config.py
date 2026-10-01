"""Central configuration. Every provider/model choice is reachable from here."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    log_level: str = "INFO"
    api_title: str = "ContentBridge API"

    # Database
    database_url: str = (
        "postgresql+asyncpg://contentbridge:contentbridge@localhost:5544/contentbridge"
    )
    db_echo: bool = False

    # Vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "contentbridge_chunks"

    # Auth
    jwt_secret: str = "dev-only-secret-replace-me-with-48-random-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    # Storage
    storage_backend: Literal["local"] = "local"
    storage_local_dir: str = "./storage"
    max_upload_mb: int = 50

    # LLM
    llm_provider: Literal["gemini", "openai_compatible", "stub"] = "gemini"
    llm_model: str = "gemini-flash-latest"
    # Comma-separated models tried in order when the main one is overloaded
    # (503/429) or retired (404).
    llm_fallback_model: str = (
        "gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash,"
        "gemini-flash-lite-latest,gemini-3.5-flash-lite"
    )
    llm_temperature: float = 0.2
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Embeddings
    embedding_provider: Literal["local_fastembed", "gemini", "openai_compatible"] = (
        "local_fastembed"
    )
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
