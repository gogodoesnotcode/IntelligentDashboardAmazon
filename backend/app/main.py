# backend/app/main.py
# FastAPI entrypoint — instance, CORS, static mount, router include. Nothing else.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routes import router

app = FastAPI(title="Moonshot Competitive Intelligence Dashboard API")

if settings.ENV == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)

# In prod, the frontend is built and served from the same origin as the API.
if settings.ENV == "prod" and settings.FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=settings.FRONTEND_DIST_DIR, html=True), name="frontend")
