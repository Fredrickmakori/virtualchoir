from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.services.accounts import list_admin_users
from backend.services.leads import list_pilot_leads
from backend.services.security import admin_user_context
from backend.services.supabase_client import SupabaseIntegrationError


router = APIRouter(prefix="/admin", tags=["admin"])


class AdminSubscriptionPayload(BaseModel):
    user_id: str | None = None
    payment_provider: str | None = None
    plan_name: str | None = None
    amount: int | None = None
    currency: str | None = None
    status: str | None = None
    payhero_reference: str | None = None
    payhero_external_reference: str | None = None
    payhero_checkout_request_id: str | None = None
    payhero_provider_reference: str | None = None
    payhero_phone_number: str | None = None
    transaction_date: str | None = None
    updated_at: str | None = None


class AdminUserPayload(BaseModel):
    id: str | None = None
    email: str | None = None
    full_name: str | None = None
    role: str
    email_confirmed_at: str | None = None
    created_at: str | None = None
    subscription: AdminSubscriptionPayload | None = None


class AdminLeadPayload(BaseModel):
    id: str
    contact_name: str
    email: str
    organization: str
    choir_type: str | None = None
    choir_size: str | None = None
    notes: str | None = None
    status: str
    source: str
    submitted_at: str


class AdminOverviewResponse(BaseModel):
    users: list[AdminUserPayload]
    leads: list[AdminLeadPayload]
    counts: dict[str, int]


@router.get("/overview", response_model=AdminOverviewResponse)
def admin_overview(_: dict = Depends(admin_user_context)) -> AdminOverviewResponse:
    try:
        users = [AdminUserPayload(**user) for user in list_admin_users()]
        leads = [AdminLeadPayload(**lead) for lead in list_pilot_leads()]
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AdminOverviewResponse(
        users=users,
        leads=leads,
        counts={"users": len(users), "leads": len(leads)},
    )
