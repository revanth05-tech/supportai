"""Configuration loaded from environment variables and an optional local .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central application settings; secrets must be supplied outside source control."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="AI Support Agent API",
        validation_alias="APP_NAME",
    )

    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )

    debug: bool = Field(
        default=False,
        validation_alias="DEBUG",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://localhost/supportai",
        validation_alias="DATABASE_URL",
    )

    jwt_secret_key: str | None = Field(
        default=None,
        validation_alias="JWT_SECRET_KEY",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
    )

    jwt_issuer: str = Field(
        default="ai-support-agent-api",
        validation_alias="JWT_ISSUER",
    )

    jwt_audience: str = Field(
        default="ai-support-agent-client",
        validation_alias="JWT_AUDIENCE",
    )

    access_token_expire_minutes: int = Field(
        default=15,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    refresh_token_expire_days: int = Field(
        default=30,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )

    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias="FRONTEND_URL",
    )

    cors_allowed_origins: list[str] | None = Field(
        default=None,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    data_protection_key: str | None = Field(
        default=None,
        validation_alias="DATA_PROTECTION_KEY",
    )

    resend_api_key: str | None = Field(
        default=None,
        validation_alias="RESEND_API_KEY",
    )

    email_from: str = Field(
        default="AI Support Agent <onboarding@resend.dev>",
        validation_alias="EMAIL_FROM",
    )
    shared_llm_api_key: str | None = Field(
        default=None,
        validation_alias="SHARED_LLM_API_KEY",
    )

    shared_llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="SHARED_LLM_BASE_URL",
    )

    shared_llm_model: str = Field(
        default="openai/gpt-4o-mini",
        validation_alias="SHARED_LLM_MODEL",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_cors_allowed_origins(config: Settings = settings) -> list[str]:
    """Return the explicit browser origins allowed to call the API.

    ``CORS_ALLOWED_ORIGINS`` is available for deployments that serve the
    dashboard from more than one known origin.  Local development deliberately
    permits both common loopback forms without relaxing credentialed CORS.
    """

    if config.cors_allowed_origins:
        return list(dict.fromkeys(config.cors_allowed_origins))

    origins = [config.frontend_url]
    if config.environment.lower() == "development":
        origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
    return list(dict.fromkeys(origins))
