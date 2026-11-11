from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AAROH"
    environment: str = "development"  # development | production | test
    database_url: str = "postgresql+psycopg://aaroh:aaroh@localhost:5432/aaroh"

    # Security
    secret_key: str = "change-me-in-production-use-64-random-chars"
    # Separate key used to encrypt user-supplied AI API keys at rest (Fernet, derived via SHA-256)
    encryption_key: str = ""
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080,capacitor://localhost,https://localhost,http://localhost"
    cookie_secure: bool = False  # set True behind HTTPS in production

    # Storage
    upload_dir: str = "./uploads"
    # disk: files in upload_dir. database: bytes stored in Postgres (for hosts with no persistent disk, e.g. free tiers)
    upload_storage: str = "disk"
    # When set, the API also serves the built web app from this folder (single-service deploys)
    static_dir: str = ""
    max_upload_mb: int = 8

    # AI (server-level defaults; users may override with their own key in Settings)
    ai_provider: str = "none"  # none | anthropic | openai_compatible
    ai_model: str = ""
    ai_base_url: str = ""  # for openai_compatible (e.g. https://api.openai.com/v1, http://ollama:11434/v1)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        # Hosted Postgres providers (Neon, Render, Supabase) hand out postgres:// or postgresql:// URLs
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
