# backend/app/api/routes.py
# Thin endpoints only — validate, call one repository/run_*() function,
# translate a missing result into an HTTPException.

from fastapi import APIRouter, HTTPException

from app.data import repository
from app.models.api_models import SummaryResponse, BrandAnalysis

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/summary", response_model=SummaryResponse)
def get_summary():
    summary = repository.get_summary()
    if summary is None:
        raise HTTPException(404, "No analysis data found — run agent/run_analysis.py first.")
    return summary


@router.get("/brands", response_model=list[str])
def list_brands():
    return repository.list_brands()


@router.get("/brands/{brand}", response_model=BrandAnalysis)
def get_brand(brand: str):
    analysis = repository.get_brand(brand)
    if analysis is None:
        raise HTTPException(404, f"No analysis data for brand '{brand}'.")
    return analysis
