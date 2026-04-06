from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services.accounts import AuthenticationError, sign_in_user, sign_up_user
from backend.services.security import current_user_context
from backend.services.supabase_client import SupabaseIntegrationError


router = APIRouter(prefix="/auth", tags=["auth"])
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class SessionPayload(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    expires_at: int | None = None
    token_type: str | None = None


class SubscriptionPayload(BaseModel):
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


class AppUserPayload(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    role: str
    created_at: str | None = None
    subscription: SubscriptionPayload | None = None


class AuthResponse(BaseModel):
    message: str
    needs_email_confirmation: bool
    user: AppUserPayload
    session: SessionPayload | None = None


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest) -> AuthResponse:
    try:
        response = sign_up_user(email=payload.email, password=payload.password, full_name=payload.full_name)
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AuthResponse(**response)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        response = sign_in_user(email=payload.email, password=payload.password)
    except SupabaseIntegrationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AuthResponse(**response)


@router.get("/me", response_model=AppUserPayload)
def me(app_user: dict = Depends(current_user_context)) -> AppUserPayload:
    return AppUserPayload(**app_user)


@router.post("/logout")
def logout() -> dict[str, str]:
    return {"message": "Clear the stored access token on the client to sign out."}
