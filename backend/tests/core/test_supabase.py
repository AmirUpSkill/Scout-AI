from typing import Any

import pytest

from app.core.config import Settings
from app.core import supabase as supabase_core
from app.core.supabase import SupabaseConfigurationError


@pytest.fixture(autouse=True)
def reset_clients() -> None:
    supabase_core.reset_supabase_clients()


def make_settings(**overrides: Any) -> Settings:
    values = {
        "app_name": "Scout API",
        "app_env": "local",
        "app_version": "0.1.0",
        "debug": True,
        "google_api_key": "",
        "google_model": "gemini-3.1-pro-preview",
        "supabase_url": "",
        "supabase_anon_key": "",
        "supabase_service_role_key": "",
        "auth_required": False,
        "cors_origins": ["http://localhost:3000"],
        "log_level": "INFO",
    }
    values.update(overrides)
    return Settings.model_construct(**values)


@pytest.mark.asyncio
async def test_anon_client_returns_none_when_local_config_is_optional() -> None:
    settings = make_settings(auth_required=False)

    client = await supabase_core.get_supabase_anon_client(settings)

    assert client is None


@pytest.mark.asyncio
async def test_anon_client_raises_when_auth_required_and_config_missing() -> None:
    settings = make_settings(auth_required=True)

    with pytest.raises(SupabaseConfigurationError, match="SUPABASE_URL"):
        await supabase_core.get_supabase_anon_client(settings)


@pytest.mark.asyncio
async def test_service_client_raises_when_auth_required_and_config_missing() -> None:
    settings = make_settings(auth_required=True)

    with pytest.raises(SupabaseConfigurationError, match="SUPABASE_SERVICE_ROLE_KEY"):
        await supabase_core.get_supabase_service_client(settings)


@pytest.mark.asyncio
async def test_anon_client_uses_anon_key(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    expected_client = object()
    settings = make_settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
        supabase_service_role_key="service-key",
    )

    async def fake_create_async_client(
        supabase_url: str,
        supabase_key: str,
        options: Any = None,
    ) -> object:
        calls.append((supabase_url, supabase_key))
        assert options.auto_refresh_token is False
        assert options.persist_session is False
        return expected_client

    monkeypatch.setattr(supabase_core, "create_async_client", fake_create_async_client)

    client = await supabase_core.get_supabase_anon_client(settings)

    assert client is expected_client
    assert calls == [("https://example.supabase.co", "anon-key")]


@pytest.mark.asyncio
async def test_service_client_uses_service_role_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    expected_client = object()
    settings = make_settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
        supabase_service_role_key="service-key",
    )

    async def fake_create_async_client(
        supabase_url: str,
        supabase_key: str,
        options: Any = None,
    ) -> object:
        calls.append((supabase_url, supabase_key))
        assert options.auto_refresh_token is False
        assert options.persist_session is False
        return expected_client

    monkeypatch.setattr(supabase_core, "create_async_client", fake_create_async_client)

    client = await supabase_core.get_supabase_service_client(settings)

    assert client is expected_client
    assert calls == [("https://example.supabase.co", "service-key")]
