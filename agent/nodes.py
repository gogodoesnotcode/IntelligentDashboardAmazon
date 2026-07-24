# agent/nodes.py
# One function per graph node.
# Each node reads from AgentState, calls the LLM with structured output,
# and returns a dict of fields to merge back into state.

import os
import logging
import pandas as pd
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from schemas import (
    SentimentOutput, ThemeOutput, AspectOutput, InsightsOutput,
)
from prompts import (
    SENTIMENT_PROMPT, THEME_PROMPT, ASPECT_PROMPT, INSIGHTS_PROMPT,
)

log = logging.getLogger(__name__)

# ── LLM factory ───────────────────────────────────────────────────────────────

def _llm(temperature: float = 0.2):
    """
    Low temperature (0.2) for analytical nodes that need consistency.
    Structured output is enforced via .with_structured_output().
    """
    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=temperature,
    )


# ── Review text helpers ────────────────────────────────────────────────────────

def _format_reviews(reviews: list[dict], max_reviews: int = 60) -> str:
    """
    Convert review dicts to a numbered text block for the prompt.
    Caps at max_reviews to stay within token limits — takes a spread
    across the list rather than just the first N, so all star levels
    are represented.
    """
    if not reviews:
        return "No reviews available."

    # Sample evenly across the list if we need to trim
    if len(reviews) > max_reviews:
        step = len(reviews) / max_reviews
        reviews = [reviews[int(i * step)] for i in range(max_reviews)]

    lines = []
    for i, r in enumerate(reviews, 1):
        stars = f"{r.get('stars', '?')}★"
        text  = str(r.get("text", "")).strip().replace("\n", " ")
        verified = " [verified]" if r.get("verified") else ""
        lines.append(f"{i}. [{stars}{verified}] {text}")

    return "\n".join(lines)


def _batch_reviews(reviews: list[dict], batch_size: int = 50) -> list[list[dict]]:
    """Split reviews into batches for sentiment averaging on large datasets."""
    return [reviews[i:i + batch_size] for i in range(0, len(reviews), batch_size)]


# ── Node 1: loader ─────────────────────────────────────────────────────────────

def loader_node(state: dict) -> dict:
    """
    Read the raw CSVs for the current brand into state.
    Validates that files exist and contain usable data.
    Sets an error flag if loading fails so downstream nodes can skip gracefully.
    """
    brand     = state["brand"]
    data_dir  = state.get("data_dir", "data/raw")
    slug      = brand.lower().replace(" ", "_")

    prod_path = os.path.join(data_dir, f"{slug}_products.csv")
    rev_path  = os.path.join(data_dir, f"{slug}_reviews.csv")

    errors = list(state.get("errors", []))

    # Load products
    try:
        products_df = pd.read_csv(prod_path)
        products = products_df.to_dict(orient="records")
        log.info(f"  Loaded {len(products)} products for {brand}")
    except FileNotFoundError:
        errors.append(f"Products file not found: {prod_path}")
        products = []
    except Exception as e:
        errors.append(f"Error loading products: {e}")
        products = []

    # Load reviews
    try:
        reviews_df = pd.read_csv(rev_path)
        # Drop rows with empty text
        reviews_df = reviews_df[reviews_df["text"].notna() & (reviews_df["text"].str.strip() != "")]
        reviews = reviews_df.to_dict(orient="records")
        log.info(f"  Loaded {len(reviews)} reviews for {brand}")
    except FileNotFoundError:
        errors.append(f"Reviews file not found: {rev_path}")
        reviews = []
    except Exception as e:
        errors.append(f"Error loading reviews: {e}")
        reviews = []

    if len(reviews) < 3:
        errors.append(f"Insufficient reviews for meaningful analysis ({len(reviews)} found, minimum 3).")

    return {
        "products": products,
        "reviews":  reviews,
        "errors":   errors,
    }


# ── Node 2: sentiment ──────────────────────────────────────────────────────────

def sentiment_node(state: dict) -> dict:
    """
    Score overall brand sentiment from customer reviews.

    For brands with >50 reviews, we batch into groups of 50, score each
    batch separately, then average — this avoids truncation and gives a
    more representative score than just taking the first 50 reviews.
    """
    brand   = state["brand"]
    reviews = state.get("reviews", [])

    if not reviews:
        log.warning(f"  No reviews for sentiment node ({brand}), skipping.")
        return {
            "sentiment_score": 5.0,
            "sentiment_label": "mixed",
            "sentiment_summary": "Insufficient review data for sentiment analysis.",
        }

    structured_llm = _llm(temperature=0.1).with_structured_output(SentimentOutput)

    batches     = _batch_reviews(reviews, batch_size=50)
    all_scores  = []
    last_output = None

    for batch_num, batch in enumerate(batches, 1):
        log.info(f"  Sentiment batch {batch_num}/{len(batches)} for {brand} ({len(batch)} reviews)")
        reviews_text = _format_reviews(batch, max_reviews=50)

        prompt = SENTIMENT_PROMPT.format(
            brand=brand,
            review_count=len(batch),
            reviews_text=reviews_text,
        )

        try:
            output: SentimentOutput = structured_llm.invoke([HumanMessage(content=prompt)])
            all_scores.append(output.score)
            last_output = output
        except Exception as e:
            log.error(f"  Sentiment batch {batch_num} failed: {e}")
            errors = list(state.get("errors", []))
            errors.append(f"Sentiment batch {batch_num} error: {e}")

    if not all_scores:
        return {
            "sentiment_score": 5.0,
            "sentiment_label": "mixed",
            "sentiment_summary": "Sentiment analysis failed — LLM error.",
            "errors": state.get("errors", []),
        }

    avg_score = round(sum(all_scores) / len(all_scores), 2)

    # Use the label from the last batch but recalculate based on averaged score
    label = "positive" if avg_score >= 7.0 else ("negative" if avg_score <= 4.0 else "mixed")

    log.info(f"  Sentiment for {brand}: {avg_score} ({label})")

    return {
        "sentiment_score":   avg_score,
        "sentiment_label":   label,
        "sentiment_summary": last_output.summary if last_output else "",
    }


# ── Node 3: themes ─────────────────────────────────────────────────────────────

def theme_node(state: dict) -> dict:
    """
    Extract the top 5 praise and top 5 complaint themes across all reviews.
    Runs on a sample of up to 60 reviews to stay within a single LLM call.
    """
    brand   = state["brand"]
    reviews = state.get("reviews", [])

    if not reviews:
        return {
            "praise_themes":    [],
            "complaint_themes": [],
        }

    reviews_text   = _format_reviews(reviews, max_reviews=60)
    structured_llm = _llm(temperature=0.2).with_structured_output(ThemeOutput)

    prompt = THEME_PROMPT.format(
        brand=brand,
        review_count=min(len(reviews), 60),
        reviews_text=reviews_text,
    )

    try:
        output: ThemeOutput = structured_llm.invoke([HumanMessage(content=prompt)])
        log.info(f"  Themes for {brand}: {len(output.praise_themes)} praise, {len(output.complaint_themes)} complaint")
        return {
            "praise_themes":    output.praise_themes,
            "complaint_themes": output.complaint_themes,
        }
    except Exception as e:
        log.error(f"  Theme node failed for {brand}: {e}")
        errors = list(state.get("errors", []))
        errors.append(f"Theme node error: {e}")
        return {
            "praise_themes":    [],
            "complaint_themes": [],
            "errors": errors,
        }


# ── Node 4: aspects ────────────────────────────────────────────────────────────

def aspect_node(state: dict) -> dict:
    """
    Score 6 product aspects (wheels, handle, zipper, material, size, durability)
    plus a value-for-money assessment that compares quality signals to price band.
    """
    brand    = state["brand"]
    reviews  = state.get("reviews", [])
    products = state.get("products", [])

    if not reviews:
        return {"aspect_scores": {}, "value_for_money": {}}

    # Calculate average selling price across scraped products
    prices = [
        p.get("price") for p in products
        if p.get("price") is not None
    ]
    avg_price = round(sum(prices) / len(prices), 0) if prices else 0

    reviews_text   = _format_reviews(reviews, max_reviews=60)
    structured_llm = _llm(temperature=0.1).with_structured_output(AspectOutput)

    prompt = ASPECT_PROMPT.format(
        brand=brand,
        review_count=min(len(reviews), 60),
        avg_price=int(avg_price),
        reviews_text=reviews_text,
    )

    try:
        output: AspectOutput = structured_llm.invoke([HumanMessage(content=prompt)])

        aspect_scores = {
            "wheels":    {"score": output.wheels.score,    "summary": output.wheels.summary},
            "handle":    {"score": output.handle.score,    "summary": output.handle.summary},
            "zipper":    {"score": output.zipper.score,    "summary": output.zipper.summary},
            "material":  {"score": output.material.score,  "summary": output.material.summary},
            "size":      {"score": output.size.score,      "summary": output.size.summary},
            "durability":{"score": output.durability.score,"summary": output.durability.summary},
        }
        value_for_money = {
            "score":      output.value_for_money.score,
            "price_band": output.value_for_money.price_band,
            "verdict":    output.value_for_money.verdict,
            "avg_price":  avg_price,
        }

        log.info(f"  Aspects scored for {brand} | VFM: {output.value_for_money.score} ({output.value_for_money.price_band})")

        return {
            "aspect_scores":  aspect_scores,
            "value_for_money": value_for_money,
        }

    except Exception as e:
        log.error(f"  Aspect node failed for {brand}: {e}")
        errors = list(state.get("errors", []))
        errors.append(f"Aspect node error: {e}")
        return {
            "aspect_scores":   {},
            "value_for_money": {},
            "errors": errors,
        }


# ── Node 5: insights ───────────────────────────────────────────────────────────

def insights_node(state: dict) -> dict:
    """
    Cross-brand insights node — runs after all brands are analyzed.
    Receives the full all_brands_summary dict (built by writer_node in
    previous iterations) and generates 5 non-obvious conclusions.

    This node is SKIPPED for intermediate brands and only executes
    when state["is_last_brand"] is True (set by run_analysis.py).
    """
    if not state.get("is_last_brand", False):
        return {}

    all_brands_summary = state.get("all_brands_summary", {})

    if len(all_brands_summary) < 2:
        log.warning("  Insights node: fewer than 2 brands in summary, skipping.")
        return {"insights": []}

    # Build a readable summary block for the prompt
    summary_lines = []
    for brand, data in all_brands_summary.items():
        summary_lines.append(f"\n### {brand}")
        summary_lines.append(f"  Sentiment: {data.get('sentiment_score', 'N/A')} / 10 ({data.get('sentiment_label', '')})")
        summary_lines.append(f"  Sentiment summary: {data.get('sentiment_summary', '')}")
        summary_lines.append(f"  Top praise:    {', '.join(data.get('praise_themes', []))}")
        summary_lines.append(f"  Top complaints:{', '.join(data.get('complaint_themes', []))}")
        vfm = data.get("value_for_money", {})
        summary_lines.append(f"  Avg price: ₹{vfm.get('avg_price', 'N/A')} ({vfm.get('price_band', '')})")
        summary_lines.append(f"  Value-for-money score: {vfm.get('score', 'N/A')} — {vfm.get('verdict', '')}")
        aspects = data.get("aspect_scores", {})
        if aspects:
            aspect_str = " | ".join(f"{k}: {v['score']}" for k, v in aspects.items())
            summary_lines.append(f"  Aspect scores: {aspect_str}")

    brand_summaries = "\n".join(summary_lines)
    structured_llm  = _llm(temperature=0.4).with_structured_output(InsightsOutput)

    prompt = INSIGHTS_PROMPT.format(
        brand_count=len(all_brands_summary),
        brand_summaries=brand_summaries,
    )

    try:
        output: InsightsOutput = structured_llm.invoke([HumanMessage(content=prompt)])
        insights = [
            {"headline": ins.headline, "explanation": ins.explanation}
            for ins in output.insights
        ]
        log.info(f"  Generated {len(insights)} cross-brand insights")
        return {"insights": insights}

    except Exception as e:
        log.error(f"  Insights node failed: {e}")
        errors = list(state.get("errors", []))
        errors.append(f"Insights node error: {e}")
        return {"insights": [], "errors": errors}


# ── Node 6: writer ─────────────────────────────────────────────────────────────

def writer_node(state: dict) -> dict:
    """
    Serialize the current brand's analysis to disk and update the
    accumulated all_brands_summary dict for the insights node.
    """
    import json

    brand      = state["brand"]
    output_dir = state.get("output_dir", "data/analyzed")
    os.makedirs(output_dir, exist_ok=True)

    brand_result = {
        "brand":             brand,
        "product_count":     len(state.get("products", [])),
        "review_count":      len(state.get("reviews", [])),
        "sentiment_score":   state.get("sentiment_score"),
        "sentiment_label":   state.get("sentiment_label"),
        "sentiment_summary": state.get("sentiment_summary"),
        "praise_themes":     state.get("praise_themes", []),
        "complaint_themes":  state.get("complaint_themes", []),
        "aspect_scores":     state.get("aspect_scores", {}),
        "value_for_money":   state.get("value_for_money", {}),
        "insights":          state.get("insights", []),
        "errors":            state.get("errors", []),
    }

    slug = brand.lower().replace(" ", "_")
    out_path = os.path.join(output_dir, f"{slug}_analysis.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(brand_result, f, indent=2, ensure_ascii=False)

    log.info(f"  Saved analysis → {out_path}")

    # Accumulate into the cross-brand summary for insights_node
    all_brands_summary = dict(state.get("all_brands_summary", {}))
    all_brands_summary[brand] = brand_result

    return {"all_brands_summary": all_brands_summary}
