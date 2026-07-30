from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = secrets.token_hex(32)
    encryption_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./knowledge_platform.db"
    hf_token: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    image_open_api_key: str = ""
    image_processing_model: str = "gpt-5-nano"
    embedding_model: str = "all-mpnet-base-v2"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_use_tls: bool = True
    max_upload_size_mb: int = 100
    upload_dir: str = "uploads"
    allowed_origins: str = "http://localhost:8000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def generate_encryption_key_if_missing(self) -> Settings:
        """
        Auto-generate a Fernet encryption key if none is configured.
        In production, ENCRYPTION_KEY must be set explicitly in .env.
        """
        if not self.encryption_key:
            from cryptography.fernet import Fernet

            self.encryption_key = Fernet.generate_key().decode()
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
