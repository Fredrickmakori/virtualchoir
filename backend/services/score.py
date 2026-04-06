from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORE_UPLOADS_DIR = PROJECT_ROOT / "uploads" / "scores"
OMR_OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "omr"
MUSICXML_EXTENSIONS = {".musicxml", ".xml", ".mxl"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_SCORE_EXTENSIONS = MUSICXML_EXTENSIONS | PDF_EXTENSIONS


class ScorePreparationError(RuntimeError):
    """Raised when an uploaded score cannot be prepared for parsing."""


def ensure_score_directories() -> None:
    SCORE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OMR_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_score_extension(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_SCORE_EXTENSIONS:
        raise ValueError(
            "Unsupported score type. Please upload MusicXML (.musicxml, .xml, .mxl) or PDF (.pdf)."
        )

    return suffix


def resolve_audiveris_bin(configured_path: str | Path | None = None) -> Path:
    candidates = [
        Path(configured_path).expanduser() if configured_path else None,
        Path(os.environ["AUDIVERIS_BIN"]).expanduser() if os.environ.get("AUDIVERIS_BIN") else None,
        Path(shutil.which("audiveris")) if shutil.which("audiveris") else None,
        Path(shutil.which("Audiveris")) if shutil.which("Audiveris") else None,
        Path("C:/Program Files/Audiveris/bin/Audiveris.exe"),
        Path("C:/Program Files/Audiveris/bin/Audiveris.bat"),
        Path("C:/Program Files/Audiveris/Audiveris.exe"),
        Path("C:/Program Files (x86)/Audiveris/bin/Audiveris.exe"),
    ]

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "PDF score support requires Audiveris. Install Audiveris and set AUDIVERIS_BIN if it is not on PATH."
    )


def convert_pdf_to_musicxml(
    pdf_path: str | Path,
    output_dir: str | Path,
    audiveris_bin: str | Path | None = None,
) -> Path:
    source_pdf = Path(pdf_path)
    if not source_pdf.exists():
        raise FileNotFoundError(f"PDF score not found: {source_pdf}")

    resolved_audiveris = resolve_audiveris_bin(audiveris_bin)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(resolved_audiveris),
        "-batch",
        "-transcribe",
        "-export",
        "-output",
        str(target_dir),
        str(source_pdf),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if completed.returncode != 0:
        error_output = completed.stderr.strip() or completed.stdout.strip() or "Unknown Audiveris error."
        raise ScorePreparationError(f"Audiveris failed to convert the PDF score: {error_output}")

    generated_files = sorted(
        list(target_dir.glob("*.mxl")) + list(target_dir.glob("*.musicxml")) + list(target_dir.glob("*.xml"))
    )
    if not generated_files:
        raise ScorePreparationError("Audiveris finished, but no MusicXML output was created.")

    preferred_match = next((path for path in generated_files if path.stem.startswith(source_pdf.stem)), None)
    return (preferred_match or generated_files[0]).resolve()


def prepare_score_for_parsing(
    upload_path: str | Path,
    upload_id: str,
    audiveris_bin: str | Path | None = None,
) -> dict[str, str | None]:
    source_path = Path(upload_path)
    suffix = source_path.suffix.lower()

    if suffix in MUSICXML_EXTENSIONS:
        return {
            "source_type": "musicxml",
            "parse_file_path": str(source_path.resolve()),
            "converted_musicxml_path": None,
        }

    if suffix in PDF_EXTENSIONS:
        converted_dir = OMR_OUTPUTS_DIR / upload_id
        converted_path = convert_pdf_to_musicxml(
            pdf_path=source_path,
            output_dir=converted_dir,
            audiveris_bin=audiveris_bin,
        )
        return {
            "source_type": "pdf",
            "parse_file_path": str(converted_path),
            "converted_musicxml_path": str(converted_path),
        }

    raise ValueError("Unsupported score type.")
