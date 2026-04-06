from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.voice import list_voice_takes, save_voice_take


router = APIRouter(tags=["voice"])


class VoiceTakeResponse(BaseModel):
    id: str
    singer_name: str
    voice_part: str
    take_label: str | None
    notes: str | None
    original_filename: str
    stored_file_path: str
    audio_url: str
    size_bytes: int
    uploaded_at: str


@router.get("/voice-takes", response_model=list[VoiceTakeResponse])
def get_voice_takes() -> list[VoiceTakeResponse]:
    return [VoiceTakeResponse(**take) for take in list_voice_takes()]


@router.post("/upload-voice", response_model=VoiceTakeResponse)
async def upload_voice(
    singer_name: str = Form(...),
    voice_part: str = Form(...),
    take_label: str | None = Form(None),
    notes: str | None = Form(None),
    file: UploadFile = File(...),
) -> VoiceTakeResponse:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded voice file is empty.")

    try:
        take = save_voice_take(
            original_filename=file.filename,
            file_bytes=file_bytes,
            singer_name=singer_name,
            voice_part=voice_part,
            take_label=take_label,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return VoiceTakeResponse(**take)
