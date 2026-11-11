from functools import lru_cache

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
    max_upload_mb: int = 8

    # AI (server-level defaults; users may override with their own key in Settings)
    ai_provider: str = "none"  # none | anthropic | openai_compatible
    ai_model: str = ""
    ai_base_url: str = ""  # for openai_compatible (e.g. https://api.openai.com/v1, http://ollama:11434/v1)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
