from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_RATE = 44_100


def _resolve_fluidsynth_bin(configured_path: str | Path | None = None) -> Path:
    candidates = [
        Path(configured_path).expanduser() if configured_path else None,
        Path(os.environ["FLUIDSYNTH_BIN"]).expanduser() if os.environ.get("FLUIDSYNTH_BIN") else None,
        Path(shutil.which("fluidsynth")) if shutil.which("fluidsynth") else None,
    ]
    candidates.extend(PROJECT_ROOT.glob("tools/fluidsynth/**/fluidsynth.exe"))

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "FluidSynth executable not found. Set FLUIDSYNTH_BIN or place a FluidSynth binary under tools/fluidsynth."
    )


def _resolve_soundfont_path(configured_path: str | Path | None = None) -> Path:
    candidates = [
        Path(configured_path).expanduser() if configured_path else None,
        Path(os.environ["SOUNDFONT_PATH"]).expanduser() if os.environ.get("SOUNDFONT_PATH") else None,
    ]
    candidates.extend(sorted(PROJECT_ROOT.glob("tools/soundfonts/*.sf2")))

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "SoundFont not found. Set SOUNDFONT_PATH or place an .sf2 file under tools/soundfonts."
    )


def render_wav_from_midi(
    midi_path: str | Path,
    wav_path: str | Path,
    soundfont_path: str | Path | None = None,
    fluidsynth_bin: str | Path | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    source_midi = Path(midi_path)
    if not source_midi.exists():
        raise FileNotFoundError(f"MIDI file not found: {source_midi}")

    target_wav = Path(wav_path)
    target_wav.parent.mkdir(parents=True, exist_ok=True)

    resolved_fluidsynth = _resolve_fluidsynth_bin(fluidsynth_bin)
    resolved_soundfont = _resolve_soundfont_path(soundfont_path)

    command = [
        str(resolved_fluidsynth),
        "-ni",
        "-F",
        str(target_wav),
        "-T",
        "wav",
        "-r",
        str(sample_rate),
        str(resolved_soundfont),
        str(source_midi),
    ]

    env = os.environ.copy()
    env["PATH"] = f"{resolved_fluidsynth.parent}{os.pathsep}{env.get('PATH', '')}"

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        error_output = completed.stderr.strip() or completed.stdout.strip() or "Unknown FluidSynth error."
        raise RuntimeError(f"FluidSynth failed to render audio: {error_output}")

    if not target_wav.exists():
        raise RuntimeError("FluidSynth completed without producing a WAV file.")

    return target_wav
