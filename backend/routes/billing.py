from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.services.billing import BillingIntegrationError, billing_plans, create_payment_request, fetch_payment_status, handle_billing_webhook
from backend.services.security import current_user_context
from backend.services.supabase_client import SupabaseIntegrationError


router = APIRouter(prefix="/billing", tags=["billing"])


class BillingPlanPayload(BaseModel):
    plan: str
    label: str
    amount: int | None = None
    currency: str
    available: bool
    description: str


class PaymentRequestPayload(BaseModel):
    plan_name: str = Field(min_length=2, max_length=32)
    phone_number: str = Field(min_length=9, max_length=20)


class PaymentRequestResponse(BaseModel):
    reference: str | None = None
    external_reference: str
    checkout_request_id: str | None = None
    status: str | None = None
    plan_name: str
    amount: int
    currency: str


class PaymentStatusResponse(BaseModel):
    reference: str | None = None
    external_reference: str | None = None
    checkout_request_id: str | None = None
    status: str | None = None
    success: bool | None = None
    amount: int | None = None
    currency: str | None = None
    provider: str | None = None
    provider_reference: str | None = None
    phone_number: str | None = None
    transaction_date: str | None = None
    raw: dict[str, Any] | None = None


@router.get("/plans", response_model=list[BillingPlanPayload])
def get_billing_plans() -> list[BillingPlanPayload]:
    return [BillingPlanPayload(**plan) for plan in billing_plans()]


@router.post("/payment-request", response_model=PaymentRequestResponse)
def payment_request(
    payload: PaymentRequestPayload,
    app_user: dict = Depends(current_user_context),
) -> PaymentRequestResponse:
    try:
        payment = create_payment_request(
            app_user=app_user,
            plan_name=payload.plan_name,
            phone_number=payload.phone_number,
        )
    except (SupabaseIntegrationError, BillingIntegrationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PaymentRequestResponse(**payment)


@router.get("/payment-status", response_model=PaymentStatusResponse)
def payment_status(
    reference: str = Query(min_length=3),
    app_user: dict = Depends(current_user_context),
) -> PaymentStatusResponse:
    try:
        payment = fetch_payment_status(app_user=app_user, reference=reference)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BillingIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PaymentStatusResponse(**payment)


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    token: str | None = None,
) -> dict[str, Any]:
    payload = await request.body()
    try:
        return handle_billing_webhook(payload=payload, callback_token=token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except BillingIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
