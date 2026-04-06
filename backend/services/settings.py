from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"


def _load_env_file() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_int(name: str, default: int | None = None) -> int | None:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    supabase_url: str | None
    supabase_anon_key: str | None
    supabase_service_role_key: str | None
    site_url: str
    admin_emails: tuple[str, ...]
    payhero_base_url: str
    payhero_basic_auth_token: str | None
    payhero_channel_id: int | None
    payhero_provider: str
    payhero_credential_id: str | None
    payhero_network_code: str | None
    payhero_callback_token: str | None
    payhero_currency: str
    payhero_plan_amount_starter: int
    payhero_plan_amount_director: int
    payhero_plan_amount_organization: int

    @property
    def supabase_ready(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key and self.supabase_service_role_key)

    @property
    def payhero_ready(self) -> bool:
        return bool(self.payhero_basic_auth_token and self.payhero_channel_id)

    @property
    def site_is_public(self) -> bool:
        lowered = self.site_url.lower()
        return "localhost" not in lowered and "127.0.0.1" not in lowered and "[::1]" not in lowered

    def payhero_plan_amount_for(self, plan_name: str) -> int | None:
        normalized = plan_name.strip().lower()
        mapping = {
            "starter": self.payhero_plan_amount_starter,
            "director": self.payhero_plan_amount_director,
            "organization": self.payhero_plan_amount_organization,
        }
        return mapping.get(normalized)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file()

    admin_emails = tuple(
        email.strip().lower()
        for email in os.getenv("ADMIN_EMAILS", "").split(",")
        if email.strip()
    )

    return Settings(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        site_url=os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/"),
        admin_emails=admin_emails,
        payhero_base_url=os.getenv("PAYHERO_BASE_URL", "https://backend.payhero.co.ke/api/v2").rstrip("/"),
        payhero_basic_auth_token=os.getenv("PAYHERO_BASIC_AUTH_TOKEN"),
        payhero_channel_id=_read_int("PAYHERO_CHANNEL_ID"),
        payhero_provider=os.getenv("PAYHERO_PROVIDER", "m-pesa").strip().lower(),
        payhero_credential_id=os.getenv("PAYHERO_CREDENTIAL_ID"),
        payhero_network_code=os.getenv("PAYHERO_NETWORK_CODE"),
        payhero_callback_token=os.getenv("PAYHERO_CALLBACK_TOKEN"),
        payhero_currency=os.getenv("PAYHERO_CURRENCY", "KES").strip().upper(),
        payhero_plan_amount_starter=_read_int("PAYHERO_PLAN_AMOUNT_STARTER", 500) or 500,
        payhero_plan_amount_director=_read_int("PAYHERO_PLAN_AMOUNT_DIRECTOR", 1500) or 1500,
        payhero_plan_amount_organization=_read_int("PAYHERO_PLAN_AMOUNT_ORGANIZATION", 4500) or 4500,
    )
