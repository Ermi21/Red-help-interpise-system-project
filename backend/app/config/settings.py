"""
Centralized application configuration.

All configuration is sourced from environment variables (or a .env file in
development). Nothing here should ever hold secrets by default — see
.env.example for the full list of variables this backend understands.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Enterprise DB RAG Assistant"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000"]

    # --- Target company database (READ-ONLY) ---
    target_db_url: str
    target_db_pool_size: int = 5
    target_db_statement_timeout_ms: int = 15000
    target_db_max_rows_returned: int = 500

    # --- Application's own operational database (read/write, NOT the target) ---
    app_db_url: str

    # --- JWT ---
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- Groq chat generation ---
    groq_api_key: str = ""
    groq_chat_model: str = "openai/gpt-oss-120b"
    groq_request_timeout_s: int = 60

    # --- Ollama embeddings (optional) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"

    # --- ChromaDB ---
    chroma_persist_dir: str = "./vector_db"
    chroma_collection_name: str = "db_knowledge_base"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 60

    # --- Notifications ---
    notify_min_severity: str = "high"

    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_from: str = "alerts@example.com"
    alert_email_to: List[str] = Field(default_factory=list)

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    teams_enabled: bool = False
    teams_webhook_url: str = ""

    generic_webhook_enabled: bool = False
    generic_webhook_url: str = ""

    # --- Health monitoring ---
    health_check_interval_minutes: int = 60
    null_ratio_warning_threshold: float = 0.4

    # --- Logging ---
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # --- Phase 2: Redis Cache ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_enabled: bool = True

    # --- Phase 2: WebSockets ---
    websocket_enabled: bool = True
    websocket_monitoring_interval_s: int = 10

    # --- Phase 2: Connection Pooling ---
    target_db_pool_size: int = 20
    target_db_pool_max_overflow: int = 10
    target_db_pool_recycle_seconds: int = 3600
    target_db_pool_pre_ping: bool = True

    app_db_pool_size: int = 10
    app_db_pool_max_overflow: int = 5


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the environment is only parsed once per process."""
    return Settings()
