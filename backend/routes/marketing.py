from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.leads import list_pilot_leads, save_pilot_lead


router = APIRouter(tags=["marketing"])


class PilotLeadRequest(BaseModel):
    contact_name: str
    email: str
    organization: str
    choir_type: str | None = None
    choir_size: str | None = None
    notes: str | None = None


class PilotLeadResponse(BaseModel):
    id: str
    contact_name: str
    email: str
    organization: str
    choir_type: str | None
    choir_size: str | None
    notes: str | None
    status: str
    source: str
    submitted_at: str


@router.get("/pilot-interest", response_model=list[PilotLeadResponse])
def get_pilot_interest() -> list[PilotLeadResponse]:
    return [PilotLeadResponse(**lead) for lead in list_pilot_leads()]


@router.post("/pilot-interest", response_model=PilotLeadResponse, status_code=201)
def create_pilot_interest(payload: PilotLeadRequest) -> PilotLeadResponse:
    try:
        lead = save_pilot_lead(
            contact_name=payload.contact_name,
            email=payload.email,
            organization=payload.organization,
            choir_type=payload.choir_type,
            choir_size=payload.choir_size,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PilotLeadResponse(**lead)
