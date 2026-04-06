from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from backend.services.settings import get_settings
from backend.services.supabase_client import create_service_supabase_client


class BillingIntegrationError(RuntimeError):
    pass


def _require_payhero() -> tuple[Any, Any]:
    settings = get_settings()
    if not settings.payhero_ready:
        raise BillingIntegrationError(
            "PayHero is not configured. Set PAYHERO_BASIC_AUTH_TOKEN and PAYHERO_CHANNEL_ID."
        )

    try:
        import httpx
    except ImportError as exc:
        raise BillingIntegrationError(
            "The HTTP client dependency is missing. Run `pip install -r requirements.txt`."
        ) from exc

    return settings, httpx


def _payhero_headers() -> dict[str, str]:
    token = (get_settings().payhero_basic_auth_token or "").strip()
    if token.lower().startswith("basic "):
        token = token[6:].strip()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {token}",
    }


def _payhero_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings, httpx = _require_payhero()
    url = f"{settings.payhero_base_url}/{path.lstrip('/')}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                headers=_payhero_headers(),
                params=params,
                json=json_body,
            )
    except httpx.HTTPError as exc:
        raise BillingIntegrationError(f"Could not reach PayHero: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text.strip()}

    if response.status_code >= 400:
        message = (
            payload.get("detail")
            or payload.get("message")
            or payload.get("error")
            or response.text.strip()
            or f"PayHero returned HTTP {response.status_code}."
        )
        raise BillingIntegrationError(str(message))

    return payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_subscription_by(field: str, value: str | None) -> dict[str, Any] | None:
    if not value:
        return None

    response = (
        create_service_supabase_client()
        .table("subscriptions")
        .select("*")
        .eq(field, value)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return dict(data[0]) if data else None


def _find_subscription_for_user_reference(user_id: str, reference: str) -> dict[str, Any] | None:
    for field in (
        "payhero_reference",
        "payhero_external_reference",
        "payhero_checkout_request_id",
        "payhero_provider_reference",
    ):
        subscription = _find_subscription_by(field, reference)
        if subscription and subscription.get("user_id") == user_id:
            return subscription
    return None


def _save_subscription(payload: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    table = create_service_supabase_client().table("subscriptions")
    payload["updated_at"] = _now_iso()

    if existing and existing.get("id"):
        table.update(payload).eq("id", existing["id"]).execute()
        return _find_subscription_by("id", existing["id"]) or {**existing, **payload}

    response = table.insert(payload).execute()
    data = response.data or []
    return dict(data[0]) if data else payload


def _normalize_phone_number(phone_number: str) -> str:
    digits = re.sub(r"\D", "", phone_number or "")
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return digits
    if len(digits) == 9 and digits[0] in {"1", "7"}:
        return f"0{digits}"
    raise BillingIntegrationError("Enter a valid Kenyan phone number like 0712345678 or 254712345678.")


def _plan_catalog() -> list[dict[str, Any]]:
    settings = get_settings()
    return [
        {
            "plan": "starter",
            "label": "Starter",
            "amount": settings.payhero_plan_amount_for("starter"),
            "currency": settings.payhero_currency,
            "description": "One choir workspace for pilots and early testing.",
        },
        {
            "plan": "director",
            "label": "Director",
            "amount": settings.payhero_plan_amount_for("director"),
            "currency": settings.payhero_currency,
            "description": "Unlimited active scores for church and community choirs.",
        },
        {
            "plan": "organization",
            "label": "Organization",
            "amount": settings.payhero_plan_amount_for("organization"),
            "currency": settings.payhero_currency,
            "description": "Multi-ensemble billing for schools and ministries.",
        },
    ]


def billing_plans() -> list[dict[str, Any]]:
    settings = get_settings()
    return [
        {
            **plan,
            "available": bool(settings.payhero_ready and plan["amount"] and plan["amount"] > 0),
        }
        for plan in _plan_catalog()
    ]


def _plan_config(plan_name: str) -> dict[str, Any]:
    normalized = plan_name.strip().lower()
    for plan in _plan_catalog():
        if plan["plan"] == normalized:
            return plan
    raise BillingIntegrationError(f"Unknown billing plan '{plan_name}'.")


def _callback_url() -> str | None:
    settings = get_settings()
    if not settings.site_is_public:
        return None

    callback_url = f"{settings.site_url}/billing/webhook"
    if settings.payhero_callback_token:
        callback_url = f"{callback_url}?token={quote(settings.payhero_callback_token)}"
    return callback_url


def _payment_status_from_callback(response_payload: dict[str, Any]) -> str:
    callback_status = str(response_payload.get("Status") or "").strip().upper()
    result_code = response_payload.get("ResultCode")
    if callback_status == "SUCCESS" or result_code == 0:
        return "SUCCESS"
    if callback_status:
        return callback_status
    return "FAILED" if result_code not in {None, 0, "0"} else "SUCCESS"


def create_payment_request(*, app_user: dict[str, Any], plan_name: str, phone_number: str) -> dict[str, Any]:
    settings, _ = _require_payhero()
    plan = _plan_config(plan_name)
    if not plan["amount"] or plan["amount"] <= 0:
        raise BillingIntegrationError(f"The '{plan['label']}' plan amount is not configured.")

    normalized_phone = _normalize_phone_number(phone_number)
    external_reference = f"{plan['plan']}-{app_user['id'][:8]}-{uuid4().hex[:12]}"

    request_payload: dict[str, Any] = {
        "amount": plan["amount"],
        "phone_number": normalized_phone,
        "channel_id": settings.payhero_channel_id,
        "provider": settings.payhero_provider,
        "external_reference": external_reference,
        "customer_name": app_user.get("full_name") or app_user.get("email") or "VirtualChoir user",
    }

    callback_url = _callback_url()
    if callback_url:
        request_payload["callback_url"] = callback_url
    if settings.payhero_credential_id:
        request_payload["credential_id"] = settings.payhero_credential_id
    if settings.payhero_network_code:
        request_payload["network_code"] = settings.payhero_network_code

    payhero_response = _payhero_request("POST", "/payments", json_body=request_payload)
    saved_payment = _save_subscription(
        {
            "user_id": app_user["id"],
            "payment_provider": "payhero",
            "plan_name": plan["plan"],
            "amount": plan["amount"],
            "currency": plan["currency"],
            "status": payhero_response.get("status") or "QUEUED",
            "payhero_reference": payhero_response.get("reference"),
            "payhero_checkout_request_id": payhero_response.get("CheckoutRequestID")
            or payhero_response.get("checkout_request_id"),
            "payhero_external_reference": external_reference,
            "payhero_provider": settings.payhero_provider,
            "payhero_channel_id": settings.payhero_channel_id,
            "payhero_phone_number": normalized_phone,
            "provider_payload": payhero_response,
        }
    )

    return {
        "reference": saved_payment.get("payhero_reference"),
        "external_reference": external_reference,
        "checkout_request_id": saved_payment.get("payhero_checkout_request_id"),
        "status": saved_payment.get("status"),
        "plan_name": plan["plan"],
        "amount": plan["amount"],
        "currency": plan["currency"],
    }


def fetch_payment_status(*, app_user: dict[str, Any], reference: str) -> dict[str, Any]:
    subscription = _find_subscription_for_user_reference(app_user["id"], reference)
    if not subscription:
        raise LookupError("No PayHero payment record was found for this account and reference.")

    payhero_reference = subscription.get("payhero_reference") or reference
    payhero_response = _payhero_request(
        "GET",
        "/transaction-status",
        params={"reference": payhero_reference},
    )

    saved_payment = _save_subscription(
        {
            "status": payhero_response.get("status") or subscription.get("status"),
            "payhero_provider": payhero_response.get("provider") or subscription.get("payhero_provider"),
            "payhero_provider_reference": payhero_response.get("provider_reference")
            or payhero_response.get("third_party_reference")
            or subscription.get("payhero_provider_reference"),
            "provider_payload": payhero_response,
            "transaction_date": payhero_response.get("transaction_date") or subscription.get("transaction_date"),
        },
        existing=subscription,
    )

    raw = saved_payment.get("provider_payload") or payhero_response
    return {
        "reference": saved_payment.get("payhero_reference") or payhero_reference,
        "external_reference": saved_payment.get("payhero_external_reference"),
        "checkout_request_id": saved_payment.get("payhero_checkout_request_id"),
        "status": saved_payment.get("status"),
        "success": str((raw or {}).get("status") or saved_payment.get("status") or "").upper() == "SUCCESS",
        "amount": saved_payment.get("amount"),
        "currency": saved_payment.get("currency"),
        "provider": raw.get("provider") if isinstance(raw, dict) else saved_payment.get("payhero_provider"),
        "provider_reference": saved_payment.get("payhero_provider_reference"),
        "phone_number": saved_payment.get("payhero_phone_number"),
        "transaction_date": saved_payment.get("transaction_date"),
        "raw": raw if isinstance(raw, dict) else None,
    }


def handle_billing_webhook(*, payload: bytes, callback_token: str | None) -> dict[str, Any]:
    settings = get_settings()
    expected_token = settings.payhero_callback_token
    if expected_token and callback_token != expected_token:
        raise PermissionError("Invalid PayHero callback token.")

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("PayHero webhook body must be valid JSON.") from exc

    callback_response = event.get("response") or {}
    external_reference = callback_response.get("ExternalReference")
    checkout_request_id = callback_response.get("CheckoutRequestID")

    subscription = _find_subscription_by("payhero_external_reference", external_reference) or _find_subscription_by(
        "payhero_checkout_request_id",
        checkout_request_id,
    )
    if not subscription:
        return {"received": True, "matched": False}

    status = _payment_status_from_callback(callback_response)
    saved_payment = _save_subscription(
        {
            "status": status,
            "payhero_provider_reference": callback_response.get("MpesaReceiptNumber")
            or callback_response.get("TransactionID")
            or subscription.get("payhero_provider_reference"),
            "payhero_phone_number": callback_response.get("Phone") or subscription.get("payhero_phone_number"),
            "provider_payload": event,
        },
        existing=subscription,
    )
    return {
        "received": True,
        "matched": True,
        "status": saved_payment.get("status"),
        "reference": saved_payment.get("payhero_reference"),
    }
