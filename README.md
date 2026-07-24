# BagBoard

**Live demo: [moonshot-dashboard.onrender.com](https://moonshot-dashboard.onrender.com)**

A competitive-intelligence dashboard for the Indian luggage market. It
scrapes Amazon India listings and reviews for six brands (Safari, American
Tourister, VIP, Skybags, Aristocrat, Nasher Miles), runs an LLM pipeline
over the reviews to extract sentiment, recurring themes, per-aspect quality
scores and cross-brand competitive insights, and serves the result through
a FastAPI backend and a React dashboard.

Four stages, each independently runnable:

```
scraper (Playwright)  ->  agent (LangGraph + Groq)  ->  backend (FastAPI)  ->  frontend (React + Recharts)
```

## A data-integrity bug, found and fixed

The first version of the scraper matched brand names against search-result
titles and **failed open** when the title element didn't resolve — an
unconfirmed product was kept instead of rejected. That let cross-brand
contamination into the raw data (a Safari product turning up in
`VIP_products.csv`, for example), and a schema drift on one brand's CSV
went unnoticed because nothing validated the shape of what was written.

The scraper was rebuilt around a validate-then-write pipeline instead of
patched at the symptom:

- `scraper/search.py` treats search results as **candidates only** — no
  brand claim from that markup is trusted.
- `scraper/product_page.py` **confirms brand from the product page itself**
  (`#bylineInfo` / the product-details "Brand" row), not a title substring.
  An ASIN whose brand can't be positively confirmed is dropped.
- Every record passes through a pydantic model (`scraper/models.py`)
  before it's written, so a schema change is a visible diff instead of a
  silently different CSV header.
- Every rejection is logged with a reason
  (`scraper/raw/{brand}_rejections.log`), so a bad run is visible without
  opening every CSV by hand.

All six brands were re-scraped on the fixed pipeline (10 products and
45–78 reviews per brand). A seventh brand, Wildcraft, was scraped in an
earlier pass, came back effectively blocked (3 products, no reviews), and
was dropped from the final set rather than shipped thin.

## Modules

### 1. Scraper (`scraper/`)

Playwright with stealth, randomized delays, and a persistent browser
profile.

```bash
cd scraper
pip install -r requirements.txt
playwright install chromium
python pipeline.py --brands Safari --limit 3   # sample before scaling
python pipeline.py                              # full run, all 6 brands
```

Writes `raw/{brand}_products.csv`, `raw/{brand}_reviews.csv`, and
`raw/{brand}_rejections.log` per brand — the single raw-data directory
everything downstream reads from.

### 2. Agent (`agent/`)

A LangGraph pipeline (`loader -> sentiment -> themes -> aspects -> insights
-> writer`) over OpenAI's `gpt-oss-120b` served on Groq, with every
node's output enforced against a pydantic schema. Produces, per brand:
an overall sentiment score/label, top 5 praise and complaint themes, six
fixed aspect scores (wheels, handle, zipper, material, size, durability),
a value-for-money verdict weighed against the brand's actual scraped
average price, and — once, across all six brands — five cross-brand
competitive insights. Full methodology in `agent/README.md`.

```bash
cd agent
pip install -r requirements.txt
python run_analysis.py
```

Writes `agent/data/analyzed/{brand}_analysis.json` and
`agent/data/analyzed/all_brands_summary.json`.

### 3. Backend (`backend/`)

FastAPI, three endpoints over the analyzed JSON (`/api/summary`,
`/api/brands`, `/api/brands/{brand}`) — no LLM calls in this layer, it only
ever reads what the agent already wrote. See `backend/README.md`.

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Frontend (`frontend/`)

React + Vite, three screens: **Overview** (cross-brand insight cards,
sentiment table), **Brand comparison** (chip-based multi-select driving
Recharts grouped bar charts for aspect scores and value-for-money), and
**Brand drilldown** (per-brand themes, sentiment summary, VFM verdict, with
quoted review snippets and prices highlighted inline). Dark theme, minimal
dependencies — no router or state-management library. See
`frontend/README.md`.

```bash
cd frontend
npm install
npm run dev
```

## Docker / deployment

```bash
docker build -t bagboard .
docker run -p 8000:8000 bagboard
```

Single image: the frontend is built in stage 1 (Vite) and served as static
files by the FastAPI app in stage 2 (`ENV=prod`). The analyzed JSON is
baked into the image at build time — the deployed container never calls
Groq at runtime, it only serves what `agent/run_analysis.py` already
produced. `render.yaml` is a working Blueprint config for Render's free
tier; the live demo above is deployed from it.
