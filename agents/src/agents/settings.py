"""Application settings via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    app_name: str = Field(default="Daily Agent Hub", validation_alias="APP_NAME")
    api_prefix: str = Field(default="/api", validation_alias="API_PREFIX")

    api_host: str = Field(default="127.0.0.1", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    api_reload: bool = Field(default=False, validation_alias="API_RELOAD")

    cors_origins_raw: str = Field(
        default="http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5173,http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    rate_limit_default: str = Field(default="60/minute", validation_alias="RATE_LIMIT_DEFAULT")
    rate_limit_chat: str = Field(default="20/minute", validation_alias="RATE_LIMIT_CHAT")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")

    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/agents",
        validation_alias="DATABASE_URL",
    )
    sqlite_path: Path = Field(
        default=PROJECT_ROOT / "data" / "checkpoints.db",
        validation_alias="SQLITE_PATH",
    )
    checkpointer: Literal["memory", "sqlite", "postgres"] = Field(
        default="postgres",
        validation_alias="CHECKPOINTER",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: Literal["text", "json"] = Field(default="text", validation_alias="LOG_FORMAT")
    log_payloads: bool = Field(default=True, validation_alias="LOG_PAYLOADS")
    log_http_payloads: bool = Field(default=True, validation_alias="LOG_HTTP_PAYLOADS")

    static_dir: Path = Field(
        default=PACKAGE_ROOT / "static",
        validation_alias="STATIC_DIR",
    )

    @field_validator("static_dir", mode="before")
    @classmethod
    def default_static_dir(cls, value: Path | str | None) -> Path | str:
        if value is None:
            return PACKAGE_ROOT / "static"
        if isinstance(value, str) and not value.strip():
            return PACKAGE_ROOT / "static"
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def expose_docs(self) -> bool:
        return self.app_env != "production"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    apply_settings_to_env(settings)
    return settings


def apply_settings_to_env(settings: Settings) -> None:
    """Expose .env values to libraries that read os.environ directly."""
    import os

    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
