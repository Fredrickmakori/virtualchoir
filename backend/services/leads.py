from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEADS_DIR = PROJECT_ROOT / "data" / "leads"
LEADS_INDEX_PATH = LEADS_DIR / "pilot_interest.json"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load_leads() -> list[dict]:
    if not LEADS_INDEX_PATH.exists():
        return []

    return json.loads(LEADS_INDEX_PATH.read_text(encoding="utf-8"))


def _save_leads(leads: list[dict]) -> None:
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    LEADS_INDEX_PATH.write_text(json.dumps(leads, indent=2), encoding="utf-8")


def list_pilot_leads() -> list[dict]:
    leads = _load_leads()
    return sorted(leads, key=lambda item: item["submitted_at"], reverse=True)


def save_pilot_lead(
    *,
    contact_name: str,
    email: str,
    organization: str,
    choir_type: str | None = None,
    choir_size: str | None = None,
    notes: str | None = None,
) -> dict:
    clean_name = contact_name.strip()
    clean_email = email.strip().lower()
    clean_organization = organization.strip()

    if not clean_name:
        raise ValueError("Contact name is required.")

    if not EMAIL_PATTERN.match(clean_email):
        raise ValueError("A valid email address is required.")

    if not clean_organization:
        raise ValueError("Choir or organization name is required.")

    lead = {
        "id": uuid4().hex,
        "contact_name": clean_name,
        "email": clean_email,
        "organization": clean_organization,
        "choir_type": choir_type.strip() if choir_type and choir_type.strip() else None,
        "choir_size": choir_size.strip() if choir_size and choir_size.strip() else None,
        "notes": notes.strip() if notes and notes.strip() else None,
        "status": "new",
        "source": "landing_page",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    leads = _load_leads()
    leads.append(lead)
    _save_leads(leads)
    return lead
