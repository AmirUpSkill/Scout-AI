from typing import Literal

from supabase import AsyncClient, AsyncClientOptions, create_async_client

from app.core.config import Settings, get_settings


class SupabaseConfigurationError(RuntimeError):
    pass


ClientKind = Literal["anon", "service"]

_anon_client: AsyncClient | None = None
_service_client: AsyncClient | None = None


def _has_supabase_config(settings: Settings, kind: ClientKind) -> bool:
    key = (
        settings.supabase_anon_key
        if kind == "anon"
        else settings.supabase_service_role_key
    )
    return bool(settings.supabase_url and key)


def _require_supabase_config(settings: Settings, kind: ClientKind) -> None:
    if _has_supabase_config(settings, kind):
        return

    key_name = "SUPABASE_ANON_KEY" if kind == "anon" else "SUPABASE_SERVICE_ROLE_KEY"
    raise SupabaseConfigurationError(
        f"SUPABASE_URL and {key_name} are required for the Supabase {kind} client.",
    )


def _client_options() -> AsyncClientOptions:
    return AsyncClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )


async def get_supabase_anon_client(
    settings: Settings | None = None,
) -> AsyncClient | None:
    global _anon_client

    active_settings = settings or get_settings()
    if not _has_supabase_config(active_settings, "anon"):
        if active_settings.auth_required:
            _require_supabase_config(active_settings, "anon")
        return None

    if _anon_client is None:
        _anon_client = await create_async_client(
            active_settings.supabase_url,
            active_settings.supabase_anon_key,
            options=_client_options(),
        )

    return _anon_client


async def get_supabase_service_client(
    settings: Settings | None = None,
) -> AsyncClient | None:
    global _service_client

    active_settings = settings or get_settings()
    if not _has_supabase_config(active_settings, "service"):
        if active_settings.auth_required:
            _require_supabase_config(active_settings, "service")
        return None

    if _service_client is None:
        _service_client = await create_async_client(
            active_settings.supabase_url,
            active_settings.supabase_service_role_key,
            options=_client_options(),
        )

    return _service_client


def reset_supabase_clients() -> None:
    global _anon_client, _service_client
    _anon_client = None
    _service_client = None
