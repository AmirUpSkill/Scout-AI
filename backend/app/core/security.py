from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.supabase import SupabaseConfigurationError, get_supabase_anon_client


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    role: str = "authenticated"
    claims: dict[str, Any]


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": code,
            "message": message,
        },
    )


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if authorization_header is None or not authorization_header.strip():
        return None

    parts = authorization_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized(
            "INVALID_AUTH_HEADER",
            "Authorization header must use Bearer token format.",
        )

    return parts[1]


def _claims_to_dict(claims_response: Any) -> dict[str, Any]:
    if hasattr(claims_response, "claims"):
        claims = claims_response.claims
    elif isinstance(claims_response, dict):
        claims = claims_response.get("claims", claims_response)
    else:
        claims = claims_response

    if isinstance(claims, BaseModel):
        return claims.model_dump()
    if isinstance(claims, dict):
        return claims

    dumped_claims = {
        key: getattr(claims, key)
        for key in dir(claims)
        if not key.startswith("_") and not callable(getattr(claims, key))
    }
    return dumped_claims


def _current_user_from_claims(claims: dict[str, Any]) -> CurrentUser:
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized("INVALID_TOKEN", "Token does not include a valid user id.")

    email = claims.get("email")
    role = claims.get("role", "authenticated")

    return CurrentUser(
        id=user_id,
        email=email if isinstance(email, str) else None,
        role=role if isinstance(role, str) else "authenticated",
        claims=claims,
    )


async def verify_supabase_jwt(
    token: str,
    settings: Settings | None = None,
) -> CurrentUser:
    try:
        client = await get_supabase_anon_client(settings)
    except SupabaseConfigurationError as exc:
        raise _unauthorized("AUTH_NOT_CONFIGURED", str(exc)) from exc

    if client is None:
        raise _unauthorized(
            "AUTH_NOT_CONFIGURED",
            "Supabase authentication is not configured.",
        )

    try:
        claims_response = await client.auth.get_claims(token)
    except Exception as exc:
        raise _unauthorized("INVALID_TOKEN", "Token is invalid or expired.") from exc

    if claims_response is None:
        raise _unauthorized("INVALID_TOKEN", "Token is invalid or expired.")

    return _current_user_from_claims(_claims_to_dict(claims_response))


async def get_optional_current_user(
    authorization_header: str | None,
    settings: Settings | None = None,
) -> CurrentUser | None:
    active_settings = settings or get_settings()
    token = extract_bearer_token(authorization_header)

    if token is None:
        if active_settings.auth_required:
            raise _unauthorized("UNAUTHORIZED", "Authentication is required.")
        return None

    return await verify_supabase_jwt(token, active_settings)


async def get_required_current_user(
    authorization_header: str | None,
    settings: Settings | None = None,
) -> CurrentUser:
    active_settings = settings or get_settings()
    token = extract_bearer_token(authorization_header)

    if token is None:
        raise _unauthorized("UNAUTHORIZED", "Authentication is required.")

    return await verify_supabase_jwt(token, active_settings)
