# scraper/models.py
# Every scraped record passes through one of these before it's written to CSV.
# A schema change here shows up as a diff, not a silently different CSV header.

from pydantic import BaseModel


class ProductRecord(BaseModel):
    asin: str
    brand: str
    title: str
    price: float | None = None
    mrp: float | None = None
    discount_pct: float | None = None
    rating: float | None = None
    review_count: int | None = None
    scraped_at: str


class ReviewRecord(BaseModel):
    asin: str
    stars: float | None = None
    title: str = ""
    text: str
    date: str = ""
    verified: bool = False
    helpful: str = ""
    scraped_at: str
