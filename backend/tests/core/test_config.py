import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "APP_NAME",
        "APP_ENV",
        "APP_VERSION",
        "DEBUG",
        "GOOGLE_API_KEY",
        "GOOGLE_MODEL",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "AUTH_REQUIRED",
        "CORS_ORIGINS",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_settings_load_safe_defaults_without_env_file() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Scout API"
    assert settings.app_env == "local"
    assert settings.app_version == "0.1.0"
    assert settings.debug is True
    assert settings.google_api_key == ""
    assert settings.google_model == "gemini-3.1-pro-preview"
    assert settings.supabase_url == ""
    assert settings.supabase_anon_key == ""
    assert settings.supabase_service_role_key == ""
    assert settings.auth_required is False
    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert settings.log_level == "INFO"


def test_settings_load_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Scout Test API")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-test-model")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://app.example.com")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Scout Test API"
    assert settings.app_env == "test"
    assert settings.app_version == "1.2.3"
    assert settings.debug is False
    assert settings.google_api_key == "test-google-key"
    assert settings.google_model == "gemini-test-model"
    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_anon_key == "test-anon-key"
    assert settings.supabase_service_role_key == "test-service-role-key"
    assert settings.auth_required is True
    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://app.example.com",
    ]
    assert settings.log_level == "DEBUG"


def test_settings_reject_invalid_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "preview")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "TRACE")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_require_supabase_credentials_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(ValidationError, match="SUPABASE_URL"):
        Settings(_env_file=None)


def test_settings_require_supabase_credentials_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_REQUIRED", "true")

    with pytest.raises(ValidationError, match="SUPABASE_URL"):
        Settings(_env_file=None)
