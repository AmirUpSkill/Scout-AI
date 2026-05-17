from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BackendEnv = Literal["local", "development", "staging", "production", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    app_name: str = "Scout API"
    app_env: BackendEnv = "local"
    app_version: str = "0.1.0"
    debug: bool = True

    google_api_key: str = ""
    google_model: str = "gemini-3.1-pro-preview"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    auth_required: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )

    log_level: LogLevel = "INFO"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        must_validate_supabase = self.app_env == "production" or self.auth_required
        has_supabase_credentials = all(
            [
                self.supabase_url,
                self.supabase_anon_key,
                self.supabase_service_role_key,
            ],
        )

        if must_validate_supabase and not has_supabase_credentials:
            raise ValueError(
                "SUPABASE_URL, SUPABASE_ANON_KEY, and "
                "SUPABASE_SERVICE_ROLE_KEY are required when auth is required "
                "or APP_ENV is production.",
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
