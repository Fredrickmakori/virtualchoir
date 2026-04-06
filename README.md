# AI Choir Practice System

A CPU-based virtual choir MVP for score intake, practice-audio generation, singer take uploads, Supabase-backed authentication, admin roles, and PayHero billing using `FastAPI`, `music21`, MIDI, and `FluidSynth`.

For product positioning, pricing, outreach copy, and a 30-day launch plan, see `MARKETING.md`.

## What It Does

- Accepts `MusicXML` uploads
- Accepts `PDF` score uploads and converts them through `Audiveris` when available
- Parses note events with `music21`
- Extracts `pitch`, `duration`, `offset`, and rest timing
- Converts parsed parts into a valid multi-track MIDI file
- Renders MIDI to WAV with `FluidSynth` and a SoundFont
- Returns the generated WAV path and serves the audio file
- Provides a plain HTML + JavaScript multi-page frontend with routed workspaces for home, practice, studio, pilot, auth, and admin flows
- Supports singer take uploads by voice part, with optional in-browser recording
- Includes a landing-page pilot signup flow that stores director interest locally
- Adds Supabase-backed user accounts, admin roles, and payment records
- Adds PayHero M-Pesa payment APIs tied to authenticated users

## Project Structure

```text
backend/
  main.py
  routes/auth.py
  routes/admin.py
  routes/billing.py
  routes/music.py
  routes/marketing.py
  routes/voice.py
  services/accounts.py
  services/parser.py
  services/midi.py
  services/audio.py
  services/billing.py
  services/leads.py
  services/score.py
  services/security.py
  services/settings.py
  services/supabase_client.py
  services/voice.py

frontend/
  assets/
  index.html
  practice.html
  studio.html
  pilot.html
  auth.html
  admin.html

supabase/
  schema.sql

data/
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
Copy-Item .env.example .env
```

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- [http://127.0.0.1:8000/practice](http://127.0.0.1:8000/practice)
- [http://127.0.0.1:8000/studio](http://127.0.0.1:8000/studio)
- [http://127.0.0.1:8000/pilot](http://127.0.0.1:8000/pilot)
- [http://127.0.0.1:8000/auth](http://127.0.0.1:8000/auth)
- [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

## Supabase Setup

1. Create a Supabase project.
2. Open the SQL editor and run `supabase/schema.sql`.
3. Copy `.env.example` to `.env`.
4. Fill in:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `ADMIN_EMAILS`
5. Set your site URL in `SITE_URL`.

The backend reads `.env` automatically.

## PayHero Setup

Fill in these environment variables in `.env`:

- `PAYHERO_BASIC_AUTH_TOKEN`
- `PAYHERO_CHANNEL_ID`
- `PAYHERO_PROVIDER`
- `PAYHERO_PLAN_AMOUNT_STARTER`
- `PAYHERO_PLAN_AMOUNT_DIRECTOR`
- `PAYHERO_PLAN_AMOUNT_ORGANIZATION`

Optional:

- `PAYHERO_BASE_URL`
- `PAYHERO_CREDENTIAL_ID`
- `PAYHERO_NETWORK_CODE`
- `PAYHERO_CALLBACK_TOKEN`
- `PAYHERO_CURRENCY`

The official PayHero docs use `Authorization: Basic <token>`, so store the dashboard token in `PAYHERO_BASIC_AUTH_TOKEN`. Your `PAYHERO_CHANNEL_ID` comes from PayHero's "My Payment Channels" page.

If your `SITE_URL` is public, the backend will send PayHero callbacks to:

- `POST /billing/webhook`

If you are running locally on `127.0.0.1` or `localhost`, the app skips the callback URL automatically and relies on manual status refresh from the Auth page.

## API

### `POST /upload-score`

Upload a score file as multipart form data under the `file` field.

Supported score types:

- `.musicxml`
- `.xml`
- `.mxl`
- `.pdf`

Example:

```powershell
curl.exe -X POST -F "file=@tests/fixtures/sample.musicxml" http://127.0.0.1:8000/upload-score
```

Example response:

```json
{
  "message": "Score parsed and rendered successfully.",
  "source_type": "musicxml",
  "source_file_path": "uploads/scores/abc123.musicxml",
  "parse_file_path": "uploads/scores/abc123.musicxml",
  "converted_musicxml_path": null,
  "midi_file_path": "outputs/abc123.mid",
  "wav_file_path": "outputs/abc123.wav",
  "audio_url": "/outputs/abc123.wav",
  "warnings": [],
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

### `POST /upload-music`

Backward-compatible alias for `POST /upload-score`.

### `POST /upload-voice`

Upload a singer take as multipart form data.

Fields:

- `singer_name`
- `voice_part`
- `take_label` optional
- `notes` optional
- `file`

Example:

```powershell
curl.exe -X POST ^
  -F "singer_name=Jane Doe" ^
  -F "voice_part=Alto" ^
  -F "take_label=Verse pass" ^
  -F "file=@outputs/sample.wav" ^
  http://127.0.0.1:8000/upload-voice
```

### `GET /voice-takes`

Returns the uploaded studio takes, newest first.

### `POST /auth/signup`

Creates a Supabase user account and initializes a `profiles` row.

### `POST /auth/login`

Signs in through Supabase password auth and returns the session tokens.

### `GET /auth/me`

Validates the bearer token with Supabase and returns the current app user, role, and latest payment info.

### `POST /pilot-interest`

Accepts JSON from the public pilot form and stores interest locally in `data/leads/pilot_interest.json`.

Example:

```powershell
curl.exe -X POST ^
  -H "Content-Type: application/json" ^
  -d "{\"contact_name\":\"Grace Njeri\",\"email\":\"director@example.com\",\"organization\":\"St. Mark Choir\",\"choir_type\":\"Church choir\",\"choir_size\":\"24 singers\",\"notes\":\"Need SATB practice tracks for Easter repertoire.\"}" ^
  http://127.0.0.1:8000/pilot-interest
```

### `GET /pilot-interest`

Admin-only. Returns saved pilot requests, newest first.

### `GET /admin/overview`

Admin-only. Returns:

- authenticated users and their app roles
- saved pilot leads
- summary counts

### `GET /billing/plans`

Returns the configured PayHero plan slots, amounts, and whether each one is currently available.

### `POST /billing/payment-request`

Authenticated. Sends a PayHero M-Pesa STK push for the requested plan and phone number.

Example:

```powershell
curl.exe -X POST ^
  -H "Authorization: Bearer your-supabase-access-token" ^
  -H "Content-Type: application/json" ^
  -d "{\"plan_name\":\"starter\",\"phone_number\":\"0712345678\"}" ^
  http://127.0.0.1:8000/billing/payment-request
```

### `GET /billing/payment-status`

Authenticated. Polls PayHero for the latest state of a known payment reference and updates the saved Supabase record.

### `POST /billing/webhook`

PayHero callback endpoint for asynchronous payment updates.

## PDF Support With Audiveris

PDF support is optional and depends on `Audiveris` for optical music recognition.

Install Audiveris with `winget`:

```powershell
winget install -e --id audiveris.org.Audiveris --source winget
```

If Audiveris is not on `PATH`, point the app to it:

```powershell
$env:AUDIVERIS_BIN="C:\Path\To\Audiveris.exe"
```

If PDF upload is attempted without Audiveris, the API returns a clear setup error instead of failing silently.

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
- Verified the routed frontend pages and `/health`
- Verified `POST /upload-score` end-to-end with a real multipart MusicXML upload
- Verified `POST /upload-voice` with a real audio upload
- Verified `GET /voice-takes`
- Verified the frontend asset routes

## Verification Still Needed

- End-to-end Supabase auth with real project credentials
- Admin role assignment through a real Supabase project
- End-to-end PayHero STK push and webhook delivery with real keys
