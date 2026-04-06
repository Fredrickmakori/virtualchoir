from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi.encoders import jsonable_encoder

from backend.services.settings import get_settings
from backend.services.supabase_client import SupabaseIntegrationError, create_public_supabase_client, create_service_supabase_client


class AuthenticationError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


def _to_plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return jsonable_encoder(value)
    except Exception:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        return value


def _extract_user(auth_response: Any) -> dict[str, Any] | None:
    plain = _to_plain(auth_response)
    if isinstance(plain, Mapping):
        if isinstance(plain.get("user"), Mapping):
            return dict(plain["user"])
        if isinstance(plain, Mapping) and plain.get("id"):
            return dict(plain)
    return None


def _extract_session(auth_response: Any) -> dict[str, Any] | None:
    plain = _to_plain(auth_response)
    if isinstance(plain, Mapping) and isinstance(plain.get("session"), Mapping):
        return dict(plain["session"])
    return None


def _session_payload(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None

    return {
        "access_token": session.get("access_token"),
        "refresh_token": session.get("refresh_token"),
        "expires_in": session.get("expires_in"),
        "expires_at": session.get("expires_at"),
        "token_type": session.get("token_type"),
    }


def _full_name_from_user(user: Mapping[str, Any]) -> str | None:
    metadata = user.get("user_metadata") or {}
    if isinstance(metadata, Mapping):
        return metadata.get("full_name") or metadata.get("name")
    return None


def _default_role_for_email(email: str | None) -> str:
    settings = get_settings()
    if email and email.strip().lower() in settings.admin_emails:
        return "admin"
    return "user"


def _fetch_profile(user_id: str) -> dict[str, Any] | None:
    response = create_service_supabase_client().table("profiles").select("*").eq("id", user_id).limit(1).execute()
    data = _to_plain(response).get("data", [])
    return dict(data[0]) if data else None


def _fetch_subscription(user_id: str) -> dict[str, Any] | None:
    response = (
        create_service_supabase_client()
        .table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    data = _to_plain(response).get("data", [])
    return dict(data[0]) if data else None


def ensure_profile(user: Mapping[str, Any]) -> dict[str, Any]:
    user_id = str(user.get("id") or "")
    email = str(user.get("email") or "")
    if not user_id:
        raise AuthenticationError("Supabase did not return a valid user id.")

    existing = _fetch_profile(user_id)
    desired_role = existing.get("role") if existing else _default_role_for_email(email)
    if _default_role_for_email(email) == "admin":
        desired_role = "admin"

    full_name = _full_name_from_user(user) or (existing.get("full_name") if existing else None)

    payload = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "role": desired_role,
    }
    create_service_supabase_client().table("profiles").upsert(payload, on_conflict="id").execute()
    return _fetch_profile(user_id) or payload


def _app_user_payload(user: Mapping[str, Any], profile: Mapping[str, Any], subscription: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "id": str(user.get("id")),
        "email": user.get("email"),
        "full_name": profile.get("full_name") or _full_name_from_user(user),
        "role": profile.get("role", "user"),
        "created_at": profile.get("created_at") or user.get("created_at"),
        "subscription": subscription,
    }


def sign_up_user(*, email: str, password: str, full_name: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": password,
        "options": {
            "data": {"full_name": full_name},
            "email_redirect_to": f"{get_settings().site_url}/auth",
        },
    }
    response = create_public_supabase_client().auth.sign_up(payload)
    user = _extract_user(response)
    session = _extract_session(response)
    if not user:
        raise AuthenticationError("Supabase did not return a user record during sign up.")

    profile = ensure_profile(user)
    subscription = _fetch_subscription(str(user["id"]))
    return {
        "message": "Signup started successfully.",
        "needs_email_confirmation": session is None,
        "user": _app_user_payload(user, profile, subscription),
        "session": _session_payload(session),
    }


def sign_in_user(*, email: str, password: str) -> dict[str, Any]:
    response = create_public_supabase_client().auth.sign_in_with_password({"email": email, "password": password})
    user = _extract_user(response)
    session = _extract_session(response)
    if not user or not session:
        raise AuthenticationError("Supabase did not return an active session for this login.")

    profile = ensure_profile(user)
    subscription = _fetch_subscription(str(user["id"]))
    return {
        "message": "Signed in successfully.",
        "needs_email_confirmation": False,
        "user": _app_user_payload(user, profile, subscription),
        "session": _session_payload(session),
    }


def get_current_user_context(access_token: str) -> dict[str, Any]:
    if not access_token:
        raise AuthenticationError("Missing access token.")

    user_response = create_public_supabase_client().auth.get_user(access_token)
    user = _extract_user(user_response)
    if not user:
        raise AuthenticationError("Invalid or expired access token.")

    profile = ensure_profile(user)
    subscription = _fetch_subscription(str(user["id"]))
    return _app_user_payload(user, profile, subscription)


def require_admin_context(access_token: str) -> dict[str, Any]:
    app_user = get_current_user_context(access_token)
    if app_user.get("role") != "admin":
        raise AuthorizationError("This action requires an admin account.")
    return app_user


def list_admin_users() -> list[dict[str, Any]]:
    auth_response = create_service_supabase_client().auth.admin.list_users(page=1, per_page=1000)
    auth_users = _to_plain(auth_response).get("users", [])

    profiles_response = create_service_supabase_client().table("profiles").select("*").execute()
    profiles = {
        row["id"]: row
        for row in _to_plain(profiles_response).get("data", [])
        if row.get("id")
    }

    subscriptions_response = create_service_supabase_client().table("subscriptions").select("*").execute()
    subscriptions: dict[str, dict[str, Any]] = {}
    for row in _to_plain(subscriptions_response).get("data", []):
        user_id = row.get("user_id")
        if not user_id:
            continue

        existing = subscriptions.get(user_id)
        if not existing or (row.get("updated_at") or "") >= (existing.get("updated_at") or ""):
            subscriptions[user_id] = row

    users: list[dict[str, Any]] = []
    for auth_user in auth_users:
        user = dict(auth_user)
        profile = profiles.get(user.get("id"), {})
        subscription = subscriptions.get(user.get("id"))
        users.append(
            {
                "id": user.get("id"),
                "email": user.get("email"),
                "full_name": profile.get("full_name") or _full_name_from_user(user),
                "role": profile.get("role") or _default_role_for_email(user.get("email")),
                "email_confirmed_at": user.get("email_confirmed_at"),
                "created_at": profile.get("created_at") or user.get("created_at"),
                "subscription": subscription,
            }
        )

    return sorted(users, key=lambda item: item.get("created_at") or "", reverse=True)
