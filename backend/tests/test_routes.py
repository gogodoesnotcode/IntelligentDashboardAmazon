# backend/tests/test_routes.py
# Smoke test — no LLM involved, never hits the real API in CI.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_summary_or_404():
    # Passes whether or not agent/data/analyzed/all_brands_summary.json
    # exists locally — asserts the contract, not a specific dataset.
    res = client.get("/api/summary")
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        body = res.json()
        assert "brands" in body
        assert "generated_at" in body


def test_unknown_brand_404():
    res = client.get("/api/brands/NotARealBrand")
    assert res.status_code == 404
