# backend/app/core/config.py
# Single settings object, imported as `from app.core.config import settings` everywhere.

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "dev"
    # agent/data/analyzed — the combined + per-brand analysis JSON written by
    # agent/run_analysis.py. Both defaults assume the local repo layout
    # (repo-root/backend/app/core/config.py); the Docker image's COPY layout
    # is different, so the Dockerfile overrides these via env vars.
    ANALYZED_DATA_DIR: Path = Path(__file__).resolve().parents[3] / "agent" / "data" / "analyzed"
    FRONTEND_DIST_DIR: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    class Config:
        env_file = ".env"


settings = Settings()
