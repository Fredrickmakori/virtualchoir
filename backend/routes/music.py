from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.audio import render_wav_from_midi
from backend.services.midi import create_midi_file
from backend.services.parser import parse_musicxml
from backend.services.score import (
    SCORE_UPLOADS_DIR,
    ScorePreparationError,
    ensure_score_directories,
    prepare_score_for_parsing,
    resolve_score_extension,
)

router = APIRouter(tags=["music"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


class UploadMusicResponse(BaseModel):
    message: str
    source_type: str
    source_file_path: str
    parse_file_path: str
    converted_musicxml_path: str | None
    midi_file_path: str
    wav_file_path: str
    audio_url: str
    warnings: list[str]
    parsed_score: dict


def _build_output_name(filename: str | None) -> tuple[str, str]:
    try:
        suffix = resolve_score_extension(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    upload_id = uuid4().hex
    return upload_id, suffix


@router.post("/upload-score", response_model=UploadMusicResponse)
@router.post("/upload-music", response_model=UploadMusicResponse)
async def upload_music(file: UploadFile = File(...)) -> UploadMusicResponse:
    upload_id, suffix = _build_output_name(file.filename)

    ensure_score_directories()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    upload_path = SCORE_UPLOADS_DIR / f"{upload_id}{suffix}"
    midi_path = OUTPUTS_DIR / f"{upload_id}.mid"
    wav_path = OUTPUTS_DIR / f"{upload_id}.wav"

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    upload_path.write_bytes(file_bytes)

    try:
        prepared_score = prepare_score_for_parsing(upload_path=upload_path, upload_id=upload_id)
        parsed_score = parse_musicxml(prepared_score["parse_file_path"])
        if parsed_score.get("title") == upload_path.stem and file.filename:
            parsed_score["title"] = Path(file.filename).stem
        create_midi_file(parsed_score, midi_path)
        render_wav_from_midi(midi_path, wav_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ScorePreparationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    warnings: list[str] = []
    if prepared_score["source_type"] == "pdf":
        warnings.append(
            "PDF scores are converted through Audiveris OMR before playback generation, so complex layouts may need cleanup."
        )

    return UploadMusicResponse(
        message="Score parsed and rendered successfully.",
        source_type=str(prepared_score["source_type"]),
        source_file_path=(Path("uploads") / "scores" / upload_path.name).as_posix(),
        parse_file_path=Path(str(prepared_score["parse_file_path"])).resolve().relative_to(PROJECT_ROOT).as_posix(),
        converted_musicxml_path=(
            Path(str(prepared_score["converted_musicxml_path"])).resolve().relative_to(PROJECT_ROOT).as_posix()
            if prepared_score["converted_musicxml_path"]
            else None
        ),
        midi_file_path=(Path("outputs") / midi_path.name).as_posix(),
        wav_file_path=(Path("outputs") / wav_path.name).as_posix(),
        audio_url=f"/outputs/{wav_path.name}",
        warnings=warnings,
        parsed_score=parsed_score,
    )
