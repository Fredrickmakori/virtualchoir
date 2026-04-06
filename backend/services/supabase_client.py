from __future__ import annotations

from backend.services.settings import get_settings


class SupabaseIntegrationError(RuntimeError):
    pass


def _client_options():
    try:
        from supabase.client import ClientOptions
    except ImportError as exc:
        raise SupabaseIntegrationError(
            "Supabase Python SDK is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    return ClientOptions(auto_refresh_token=False, persist_session=False)


def create_public_supabase_client():
    settings = get_settings()
    if not settings.supabase_ready:
        raise SupabaseIntegrationError(
            "Supabase is not configured. Set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseIntegrationError(
            "Supabase Python SDK is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    return create_client(settings.supabase_url, settings.supabase_anon_key, options=_client_options())


def create_service_supabase_client():
    settings = get_settings()
    if not settings.supabase_ready:
        raise SupabaseIntegrationError(
            "Supabase is not configured. Set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise SupabaseIntegrationError(
            "Supabase Python SDK is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    return create_client(settings.supabase_url, settings.supabase_service_role_key, options=_client_options())
