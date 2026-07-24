# Moonshot Competitive Intelligence Dashboard

Scrapes Amazon India luggage listings for six brands (Safari, American
Tourister, VIP, Skybags, Aristocrat, Nasher Miles), runs an LLM sentiment /
theme / value-for-money analysis over the reviews, and serves the results
through a FastAPI backend + React dashboard.

## Data-integrity fix (read this first)

The original scraper's brand filter (`scraper/amazon_scraper.py`,
`get_brand_asins()`) matched brand names against search-result titles and
**failed open** when the title selector missed — an unconfirmed ASIN was
kept instead of rejected. This let cross-brand contamination into the raw
CSVs (e.g. a Safari product appearing in `VIP_products.csv`).

The scraper has been rebuilt around a validate-then-write pipeline:

- `scraper/search.py` treats search results as **candidates only** — no
  brand claim from that markup is trusted.
- `scraper/product_page.py` **confirms brand from the product page itself**
  (`#bylineInfo` or the product-details "Brand" row), not a title substring.
  An ASIN whose brand can't be positively confirmed is rejected.
- Every record passes through a pydantic model (`scraper/models.py`) before
  it's written — a schema change or drift is now a visible diff, not a
  silently different CSV header.
- Every rejection is logged with a reason to `scraper/raw/{brand}_rejections.log`,
  so a bad run is visible without opening every CSV by hand.

## Modules

### 1. Scraper (`scraper/`)

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
python pipeline.py --brands Safari --limit 3   # sample before scaling
python pipeline.py                              # full run, all 6 brands
```

Writes `raw/{brand}_products.csv`, `raw/{brand}_reviews.csv`, and
`raw/{brand}_rejections.log` per brand. `raw/` is the single raw-data
directory — `agent/` reads directly from it.

### 2. Agent (`agent/`)

LangGraph pipeline: sentiment, praise/complaint themes, per-aspect scoring,
value-for-money, and cross-brand insights. See `agent/README.md` for the
full methodology.

```bash
cd agent
pip install -r requirements.txt
python run_analysis.py
```

Writes `agent/data/analyzed/{brand}_analysis.json` and
`agent/data/analyzed/all_brands_summary.json`.

### 3. Backend (`backend/`)

FastAPI, serves the analyzed JSON — no LLM calls in this layer. See
`backend/README.md`.

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Frontend (`frontend/`)

Plain React + Vite dashboard: overview, brand comparison, product
drilldown. See `frontend/README.md`.

```bash
cd frontend
npm install
npm run dev
```

## Docker

```bash
docker build -t moonshot-dashboard .
docker run -p 8000:8000 moonshot-dashboard
```

Single image: frontend is built in stage 1 and served as static files by
the FastAPI app in stage 2 (`ENV=prod`). `render.yaml` has a minimal
free-tier deploy config for Render.

## Known limitations

- The raw CSVs currently in `scraper/raw/` predate this rebuild and may
  still contain cross-brand contamination from the old filter-fails-open
  bug. Re-run `scraper/pipeline.py` for all 6 brands before trusting the
  dashboard's numbers.
- `agent/data/analyzed/` was generated from that pre-fix data — re-run
  `agent/run_analysis.py` after re-scraping.
