from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routes.admin import router as admin_router
from backend.routes.auth import router as auth_router
from backend.routes.billing import router as billing_router
from backend.routes.marketing import router as marketing_router
from backend.routes.music import router as music_router
from backend.routes.voice import router as voice_router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

for directory in (FRONTEND_DIR, ASSETS_DIR, UPLOADS_DIR, OUTPUTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="AI Choir Practice System", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(marketing_router)
app.include_router(music_router)
app.include_router(voice_router)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


def _serve_page(filename: str) -> FileResponse:
    return FileResponse(FRONTEND_DIR / filename)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return _serve_page("index.html")


@app.get("/practice", include_in_schema=False)
def serve_practice() -> FileResponse:
    return _serve_page("practice.html")


@app.get("/studio", include_in_schema=False)
def serve_studio() -> FileResponse:
    return _serve_page("studio.html")


@app.get("/pilot", include_in_schema=False)
def serve_pilot() -> FileResponse:
    return _serve_page("pilot.html")


@app.get("/auth", include_in_schema=False)
def serve_auth() -> FileResponse:
    return _serve_page("auth.html")


@app.get("/admin", include_in_schema=False)
def serve_admin() -> FileResponse:
    return _serve_page("admin.html")
