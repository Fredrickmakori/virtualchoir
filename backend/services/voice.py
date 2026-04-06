from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOICE_UPLOADS_DIR = PROJECT_ROOT / "uploads" / "voice_takes"
VOICE_INDEX_PATH = VOICE_UPLOADS_DIR / "takes.json"
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm", ".flac"}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "take"


def _load_takes() -> list[dict]:
    if not VOICE_INDEX_PATH.exists():
        return []

    return json.loads(VOICE_INDEX_PATH.read_text(encoding="utf-8"))


def _save_takes(takes: list[dict]) -> None:
    VOICE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_INDEX_PATH.write_text(json.dumps(takes, indent=2), encoding="utf-8")


def list_voice_takes() -> list[dict]:
    takes = _load_takes()
    return sorted(takes, key=lambda item: item["uploaded_at"], reverse=True)


def save_voice_take(
    *,
    original_filename: str | None,
    file_bytes: bytes,
    singer_name: str,
    voice_part: str,
    take_label: str | None = None,
    notes: str | None = None,
) -> dict:
    if not singer_name.strip():
        raise ValueError("Singer name is required.")

    if not voice_part.strip():
        raise ValueError("Voice part is required.")

    suffix = Path(original_filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(
            "Unsupported voice file type. Please upload audio in .wav, .mp3, .m4a, .aac, .ogg, .webm, or .flac format."
        )

    VOICE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    take_id = uuid4().hex
    stored_name = f"{take_id}-{_slugify(voice_part)}-{_slugify(singer_name)}{suffix}"
    stored_path = VOICE_UPLOADS_DIR / stored_name
    stored_path.write_bytes(file_bytes)

    metadata = {
        "id": take_id,
        "singer_name": singer_name.strip(),
        "voice_part": voice_part.strip(),
        "take_label": take_label.strip() if take_label and take_label.strip() else None,
        "notes": notes.strip() if notes and notes.strip() else None,
        "original_filename": original_filename or stored_name,
        "stored_file_path": (Path("uploads") / "voice_takes" / stored_name).as_posix(),
        "audio_url": f"/uploads/voice_takes/{stored_name}",
        "size_bytes": len(file_bytes),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    takes = _load_takes()
    takes.append(metadata)
    _save_takes(takes)
    return metadata
