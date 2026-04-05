# AI Choir Practice System

A complete MVP for choir-practice audio generation using `FastAPI`, `music21`, MIDI, and `FluidSynth`.

## What It Does

- Accepts a `MusicXML` upload
- Parses note events with `music21`
- Extracts `pitch`, `duration`, `offset`, and rest timing
- Converts parsed parts into a valid multi-track MIDI file
- Renders MIDI to WAV with `FluidSynth` and a SoundFont
- Returns the generated WAV path and serves the audio file
- Provides a plain HTML + JavaScript frontend for upload and playback

## Project Structure

```text
backend/
  main.py
  routes/music.py
  services/parser.py
  services/midi.py
  services/audio.py

frontend/
  index.html

uploads/
outputs/
tools/
tests/fixtures/
```

## Python Version

Use Python `3.12`. This project was validated locally with Python `3.12.10`.

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## API

### `POST /upload-music`

Upload a `MusicXML` file as multipart form data under the `file` field.

Example:

```powershell
curl.exe -X POST -F "file=@tests/fixtures/sample.musicxml" http://127.0.0.1:8000/upload-music
```

Example response:

```json
{
  "message": "MusicXML parsed and rendered successfully.",
  "upload_file_path": "uploads/abc123.musicxml",
  "midi_file_path": "outputs/abc123.mid",
  "wav_file_path": "outputs/abc123.wav",
  "audio_url": "/outputs/abc123.wav",
  "parsed_score": {
    "title": "sample",
    "tempo_bpm": 96,
    "time_signature": "4/4",
    "parts": [
      {
        "name": "Soprano",
        "notes": [
          { "pitch": 60, "duration": 1.0, "offset": 0.0, "is_rest": false }
        ]
      }
    ]
  }
}
```

## FluidSynth and SoundFont

The project auto-discovers local defaults under:

- `tools/fluidsynth/fluidsynth-v2.5.1-win10-x64-cpp11/bin/fluidsynth.exe`
- `tools/soundfonts/synthgs-sf2_04-compat.sf2`

You can override them with environment variables:

```powershell
$env:FLUIDSYNTH_BIN="C:\path\to\fluidsynth.exe"
$env:SOUNDFONT_PATH="C:\path\to\your-soundfont.sf2"
```

## Verification Performed

- Parsed `tests/fixtures/sample.musicxml`
- Generated `outputs/sample.mid`
- Rendered `outputs/sample.wav`
- Verified the FastAPI root page and `/health`
- Verified `POST /upload-music` end-to-end with a real multipart upload
