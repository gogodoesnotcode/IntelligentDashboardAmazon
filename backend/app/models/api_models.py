# backend/app/models/api_models.py
# Response models for the HTTP layer — mirror the shape agent/schemas.py's
# nodes write into agent/data/analyzed/*.json.

from pydantic import BaseModel


class AspectScore(BaseModel):
    score: float
    summary: str


class ValueForMoney(BaseModel):
    score: float | None = None
    price_band: str | None = None
    verdict: str | None = None
    avg_price: float | None = None


class Insight(BaseModel):
    headline: str
    explanation: str


class BrandAnalysis(BaseModel):
    brand: str
    product_count: int
    review_count: int
    sentiment_score: float
    sentiment_label: str
    sentiment_summary: str
    praise_themes: list[str] = []
    complaint_themes: list[str] = []
    aspect_scores: dict[str, AspectScore] = {}
    value_for_money: ValueForMoney = ValueForMoney()
    insights: list[Insight] = []
    errors: list[str] = []


class SummaryResponse(BaseModel):
    generated_at: str
    brands: dict[str, BrandAnalysis]
    insights: list[Insight] = []
