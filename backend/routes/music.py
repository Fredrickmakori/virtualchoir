from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.audio import render_wav_from_midi
from backend.services.midi import create_midi_file
from backend.services.parser import parse_musicxml

router = APIRouter(tags=["music"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = PROJECT_ROOT / "uploads"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
ALLOWED_EXTENSIONS = {".musicxml", ".xml", ".mxl"}


class UploadMusicResponse(BaseModel):
    message: str
    upload_file_path: str
    midi_file_path: str
    wav_file_path: str
    audio_url: str
    parsed_score: dict


def _build_output_name(filename: str | None) -> tuple[str, str]:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a MusicXML file with .musicxml, .xml, or .mxl extension.",
        )

    upload_id = uuid4().hex
    return upload_id, suffix


@router.post("/upload-music", response_model=UploadMusicResponse)
async def upload_music(file: UploadFile = File(...)) -> UploadMusicResponse:
    upload_id, suffix = _build_output_name(file.filename)

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    upload_path = UPLOADS_DIR / f"{upload_id}{suffix}"
    midi_path = OUTPUTS_DIR / f"{upload_id}.mid"
    wav_path = OUTPUTS_DIR / f"{upload_id}.wav"

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    upload_path.write_bytes(file_bytes)

    try:
        parsed_score = parse_musicxml(upload_path)
        if parsed_score.get("title") == upload_path.stem and file.filename:
            parsed_score["title"] = Path(file.filename).stem
        create_midi_file(parsed_score, midi_path)
        render_wav_from_midi(midi_path, wav_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadMusicResponse(
        message="MusicXML parsed and rendered successfully.",
        upload_file_path=(Path("uploads") / upload_path.name).as_posix(),
        midi_file_path=(Path("outputs") / midi_path.name).as_posix(),
        wav_file_path=(Path("outputs") / wav_path.name).as_posix(),
        audio_url=f"/outputs/{wav_path.name}",
        parsed_score=parsed_score,
    )
