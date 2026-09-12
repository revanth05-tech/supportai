"""Configuration loaded from environment variables and an optional local .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings; secrets must be supplied outside source control."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="AI Support Agent API", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/supportai",
        validation_alias="DATABASE_URL",
    )
    jwt_secret_key: str | None = Field(default=None, validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
