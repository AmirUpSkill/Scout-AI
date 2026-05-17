from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core import security as security_core
from app.core.security import extract_bearer_token


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


def assert_http_error(exc: HTTPException, status_code: int, code: str) -> None:
    assert exc.status_code == status_code
    assert isinstance(exc.detail, dict)
    assert exc.detail["code"] == code


def test_extract_bearer_token_accepts_valid_header() -> None:
    assert extract_bearer_token("Bearer token-123") == "token-123"


def test_extract_bearer_token_accepts_case_insensitive_scheme() -> None:
    assert extract_bearer_token("bearer token-123") == "token-123"


def test_extract_bearer_token_returns_none_for_missing_header() -> None:
    assert extract_bearer_token(None) is None


@pytest.mark.parametrize(
    "header",
    [
        "Basic token-123",
        "Bearer",
        "Bearer token extra",
        "token-123",
    ],
)
def test_extract_bearer_token_rejects_malformed_header(header: str) -> None:
    with pytest.raises(HTTPException) as error:
        extract_bearer_token(header)

    assert_http_error(error.value, 401, "INVALID_AUTH_HEADER")


@pytest.mark.asyncio
async def test_optional_auth_returns_none_when_token_missing() -> None:
    settings = make_settings(auth_required=False)

    user = await security_core.get_optional_current_user(None, settings)

    assert user is None


@pytest.mark.asyncio
async def test_optional_auth_requires_token_when_auth_required() -> None:
    settings = make_settings(auth_required=True)

    with pytest.raises(HTTPException) as error:
        await security_core.get_optional_current_user(None, settings)

    assert_http_error(error.value, 401, "UNAUTHORIZED")


@pytest.mark.asyncio
async def test_required_auth_rejects_missing_token() -> None:
    settings = make_settings(auth_required=False)

    with pytest.raises(HTTPException) as error:
        await security_core.get_required_current_user(None, settings)

    assert_http_error(error.value, 401, "UNAUTHORIZED")


@pytest.mark.asyncio
async def test_verify_supabase_jwt_maps_claims_to_current_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
    )

    class FakeAuth:
        async def get_claims(self, token: str) -> SimpleNamespace:
            assert token == "valid-token"
            return SimpleNamespace(
                claims={
                    "sub": "user-123",
                    "email": "amir@example.com",
                    "role": "authenticated",
                },
            )

    fake_client = SimpleNamespace(auth=FakeAuth())

    async def fake_get_supabase_anon_client(settings_arg: Settings) -> Any:
        assert settings_arg is settings
        return fake_client

    monkeypatch.setattr(
        security_core,
        "get_supabase_anon_client",
        fake_get_supabase_anon_client,
    )

    user = await security_core.verify_supabase_jwt("valid-token", settings)

    assert user.id == "user-123"
    assert user.email == "amir@example.com"
    assert user.role == "authenticated"
    assert user.claims["sub"] == "user-123"


@pytest.mark.asyncio
async def test_verify_supabase_jwt_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key",
    )

    class FakeAuth:
        async def get_claims(self, token: str) -> None:
            assert token == "invalid-token"
            raise RuntimeError("bad token")

    fake_client = SimpleNamespace(auth=FakeAuth())

    async def fake_get_supabase_anon_client(settings_arg: Settings) -> Any:
        assert settings_arg is settings
        return fake_client

    monkeypatch.setattr(
        security_core,
        "get_supabase_anon_client",
        fake_get_supabase_anon_client,
    )

    with pytest.raises(HTTPException) as error:
        await security_core.verify_supabase_jwt("invalid-token", settings)

    assert_http_error(error.value, 401, "INVALID_TOKEN")
