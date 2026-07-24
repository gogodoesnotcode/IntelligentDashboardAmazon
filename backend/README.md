# Moonshot Competitive Intelligence Dashboard — Backend

FastAPI backend serving the React dashboard, reading analysis JSON written
by `agent/run_analysis.py`. No LLM calls happen in this layer — that's all
upstream, in `agent/`.

## Structure

- `app/main.py` — FastAPI instance, dev/prod CORS switch, frontend static mount
- `app/api/routes.py` — thin endpoints: `/api/health`, `/api/summary`, `/api/brands`, `/api/brands/{brand}`
- `app/core/config.py` — `Settings` (env-driven)
- `app/data/repository.py` — every read of `agent/data/analyzed/*.json` lives here; routes never touch disk directly
- `app/models/api_models.py` — response models mirroring `agent/schemas.py`'s output shapes
- `tests/test_routes.py` — smoke tests, no LLM/network involved

## Running

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires `agent/run_analysis.py` to have been run at least once so
`agent/data/analyzed/all_brands_summary.json` exists.

## Tests

```bash
pytest
```
