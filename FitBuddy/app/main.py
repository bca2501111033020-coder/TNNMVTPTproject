"""
main.py
-------
FastAPI application entrypoint for FitBuddy.

Run with (from the project root):
    uvicorn app.main:app --reload

Then open:
    http://127.0.0.1:8000            (the app)
    http://127.0.0.1:8000/docs       (Swagger UI)
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent

# Load <project>/.env before the Gemini modules read their settings.
load_dotenv(BASE_DIR / ".env")

from app.database import init_db  # noqa: E402
from app.routes import router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates fitbuddy.db and all tables automatically if they don't exist yet.
    init_db()
    yield


app = FastAPI(
    title="FitBuddy - AI Fitness Plan Generator",
    description="Generate a personalized 7-day workout plan and nutrition guidance using Google Gemini AI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(router)
