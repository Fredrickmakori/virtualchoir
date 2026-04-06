from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from backend.services.accounts import AuthenticationError, AuthorizationError, get_current_user_context, require_admin_context
from backend.services.supabase_client import SupabaseIntegrationError


def _extract_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer tokens.")
    return token


def current_user_context(token: str = Depends(_extract_bearer_token)) -> dict:
    try:
        return get_current_user_context(token)
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def admin_user_context(token: str = Depends(_extract_bearer_token)) -> dict:
    try:
        return require_admin_context(token)
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
