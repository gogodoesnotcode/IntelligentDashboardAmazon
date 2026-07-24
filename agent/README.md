# Agent — Sentiment & Competitive Analysis

A LangGraph pipeline that reads validated product/review CSVs from
`scraper/raw/` (the single raw-data directory — see `scraper/`) and produces
per-brand + cross-brand analysis JSON in `agent/data/analyzed/`.

## Running

```bash
cd agent
pip install -r requirements.txt
python run_analysis.py
```

Requires a `GROQ_API_KEY` in `.env` (repo root or `agent/.env`).

## Pipeline shape

One `graph.py` execution = one brand. `run_analysis.py` loops over the six
configured brands, running the graph once per brand, then writes a combined
`all_brands_summary.json` at the end.

```
loader → sentiment → themes → aspects → insights (last brand only) → writer
```

(`loader` skips straight to `writer` if no reviews were found for a brand —
see `_has_reviews` in `graph.py`.)

## Methodology

- **Model**: `ChatGroq` at low temperature (`0.1`–`0.2` for analytical nodes,
  `0.4` for the cross-brand insights node), configured in `nodes.py`'s
  `_llm()` factory. All output is schema-constrained via
  `.with_structured_output()` against the models in `schemas.py`.
- **Sentiment score** (`sentiment_node`): reviews are batched in groups of 50
  (`_batch_reviews`) to avoid truncation on large review sets; each batch is
  scored independently on a 0–10 scale and the batch scores are averaged.
  Label thresholds: `positive` ≥ 7.0, `negative` ≤ 4.0, otherwise `mixed`.
- **Themes** (`theme_node`): top 5 recurring praise themes and top 5 recurring
  complaint themes, extracted from a representative sample of up to 60
  reviews (`_format_reviews` samples evenly across the review list rather
  than taking just the first 60, so all star levels are represented). "Top 5"
  and "recurring" are both determined by the LLM's read of the sampled
  reviews — there is no separate frequency-counting pass.
- **Aspect scores** (`aspect_node`): six fixed aspects (wheels, handle,
  zipper, material, size, durability) each scored 0–10 with a one-sentence
  justification, plus a value-for-money verdict that weighs the aspect
  signals against the brand's average scraped price.
- **Cross-brand insights** (`insights_node`): runs once, after the last
  brand, over the accumulated `all_brands_summary` — 5 non-obvious
  competitive-intelligence conclusions grounded in the other nodes' output.
- **Non-fatal errors**: every node appends failures to a per-brand `errors`
  list instead of raising, so one bad LLM call doesn't abort the whole run;
  `writer_node` persists `errors` alongside the results for review.
