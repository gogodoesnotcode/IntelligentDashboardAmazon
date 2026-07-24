# backend/app/data/repository.py
# Every read of the analyzed-data files lives here — routes never touch
# disk directly. This is the file-backed analogue of a DB repository layer.

import json
import logging

from app.core.config import settings
from app.models.api_models import SummaryResponse, BrandAnalysis

log = logging.getLogger(__name__)


def _read_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_summary() -> SummaryResponse | None:
    data = _read_json(settings.ANALYZED_DATA_DIR / "all_brands_summary.json")
    if data is None:
        return None
    return SummaryResponse.model_validate(data)


def list_brands() -> list[str]:
    summary = get_summary()
    return list(summary.brands.keys()) if summary else []


def get_brand(brand: str) -> BrandAnalysis | None:
    summary = get_summary()
    if summary is None:
        return None
    # Case-insensitive lookup so /api/brands/safari and /api/brands/Safari both work
    for name, analysis in summary.brands.items():
        if name.lower() == brand.lower():
            return analysis
    return None
