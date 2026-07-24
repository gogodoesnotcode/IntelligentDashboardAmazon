# scraper/pipeline.py
# Orchestrates: candidates -> validate -> write, with rejection logging.
#
# Usage:
#   python pipeline.py                                # full run, all configured brands
#   python pipeline.py --brands Safari VIP --limit 3   # sample before scaling
#
# Output:
#   raw/{brand}_products.csv    — validated products only
#   raw/{brand}_reviews.csv     — validated reviews only
#   raw/{brand}_rejections.log  — one line per rejected ASIN, with reason

import os
import argparse
import logging

import pandas as pd

from browser import sync_playwright, launch_context, warm_up_session, sleep
from config import BRANDS, MAX_ASINS, OUTPUT_DIR, DELAY_PRODUCT, DELAY_BRAND, MIN_REVIEW_TEXT_LEN
from search import get_brand_candidates
from product_page import fetch_product
from reviews import fetch_reviews_for_asin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _log_rejection(log_path: str, asin: str, reason: str):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{asin}\t{reason}\n")


def _is_usable(review) -> bool:
    """A review only counts toward the 50+ target if it has both a star
    rating and text long enough to carry something for theme extraction —
    a rating with no text, or a one-word text, can't be summarized."""
    return (
        review.stars is not None
        and bool(review.text)
        and len(review.text) >= MIN_REVIEW_TEXT_LEN
    )


def run_brand(brand: str, page, limit: int, output_dir: str) -> dict:
    slug = brand.lower().replace(" ", "_")
    rejections_path = os.path.join(output_dir, f"{slug}_rejections.log")
    open(rejections_path, "w", encoding="utf-8").close()  # reset for this run

    candidates = get_brand_candidates(brand, page)
    if not candidates:
        log.warning(f"No candidates found for {brand}")
        return {"brand": brand, "products": 0, "reviews": 0, "usable_reviews": 0,
                "rejected": 0, "zero_review_products": 0, "pagination_blocked_at": None}

    products, all_reviews, rejected = [], [], 0
    zero_review_products = 0
    pagination_state = {"blocked": False}   # shared circuit breaker for this brand's run
    pagination_blocked_at = None

    # Walk the whole candidate pool (not just the first `limit`) since brand
    # confirmation on the product page rejects a good chunk of them (sub-brand
    # storefronts, mismatched listings) — slicing upfront would starve the
    # run instead of backfilling from candidates further down the list.
    for i, asin in enumerate(candidates, 1):
        if len(products) >= limit:
            break
        log.info(f"[{len(products)}/{limit} collected, candidate {i}/{len(candidates)}] {asin}")
        try:
            product, reason = fetch_product(asin, brand, page)
        except Exception as e:
            product, reason = None, f"error: {e}"

        if product is None:
            rejected += 1
            _log_rejection(rejections_path, asin, reason)
            log.warning(f"  Rejected {asin}: {reason}")
        else:
            products.append(product)
            was_blocked_before = pagination_state["blocked"]
            try:
                reviews = fetch_reviews_for_asin(asin, page, pagination_state)
            except Exception as e:
                log.warning(f"  Review fetch failed for {asin}: {e}")
                reviews = []
            if pagination_state["blocked"] and not was_blocked_before:
                pagination_blocked_at = asin
            all_reviews.extend(reviews)
            if len(reviews) == 0:
                zero_review_products += 1
            log.info(
                f"  {product.title[:60]}...\n"
                f"  ₹{product.price} | MRP ₹{product.mrp} | "
                f"{product.discount_pct}% off | {product.rating}★ | "
                f"{len(reviews)} reviews scraped"
            )

        sleep(DELAY_PRODUCT)

    usable_reviews = sum(1 for r in all_reviews if _is_usable(r))
    dropped_reviews = len(all_reviews) - usable_reviews

    pd.DataFrame([p.model_dump() for p in products]).to_csv(
        os.path.join(output_dir, f"{slug}_products.csv"), index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([r.model_dump() for r in all_reviews]).to_csv(
        os.path.join(output_dir, f"{slug}_reviews.csv"), index=False, encoding="utf-8-sig"
    )

    log.info(
        f"Brand: {brand}\n"
        f"  Products scraped: {len(products)}/{limit} (from {rejected + len(products)} candidates tried, "
        f"{len(candidates)} available)\n"
        f"  Reviews collected: {len(all_reviews)} (target: 50+) — "
        f"{usable_reviews} usable, {dropped_reviews} dropped (short/no rating)\n"
        f"  Pagination endpoint: "
        + (f"blocked after {pagination_blocked_at}, skipped for remaining products"
           if pagination_blocked_at else "not blocked")
        + f"\n  Products with 0 reviews: {zero_review_products}"
    )
    if zero_review_products > 0 or (products and zero_review_products / len(products) > 0.2):
        log.warning(
            f"  {brand}: review coverage is uneven across products — "
            f"brand-level synthesis needs coverage across multiple products, not one outlier"
        )

    return {
        "brand": brand,
        "products": len(products),
        "reviews": len(all_reviews),
        "usable_reviews": usable_reviews,
        "rejected": rejected,
        "zero_review_products": zero_review_products,
        "pagination_blocked_at": pagination_blocked_at,
    }


def main():
    parser = argparse.ArgumentParser(description="Amazon luggage scraper pipeline")
    parser.add_argument("--brands", nargs="+", default=BRANDS, help="Brands to scrape (default: all configured)")
    parser.add_argument("--limit", type=int, default=MAX_ASINS, help="Max products per brand")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    summary = []
    with sync_playwright() as p:
        context, page = launch_context(p)
        warm_up_session(page)

        for brand in args.brands:
            log.info(f"\n{'─'*45}\nBrand: {brand}\n{'─'*45}")
            try:
                result = run_brand(brand, page, args.limit, OUTPUT_DIR)
            except Exception as e:
                log.error(f"{brand}: run failed with unexpected error: {e}")
                result = {"brand": brand, "products": 0, "reviews": 0, "usable_reviews": 0,
                          "rejected": 0, "zero_review_products": 0, "pagination_blocked_at": None}
            summary.append(result)
            sleep(DELAY_BRAND)

        context.close()

    log.info(f"\n{'='*45}\nSCRAPE COMPLETE\n{'='*45}")
    for row in summary:
        log.info(
            f"  {row['brand']:<22} {row['products']:>3} products  "
            f"{row['reviews']:>4} reviews ({row['usable_reviews']:>4} usable)  "
            f"{row['rejected']:>3} rejected  {row['zero_review_products']:>2} zero-review products"
        )
        if row["products"] < args.limit or row["usable_reviews"] < 50:
            log.warning(
                f"  {row['brand']}: below target ({args.limit}+ products / 50+ usable reviews) — "
                f"consider re-running with adjusted throttling or documenting the shortfall"
            )


if __name__ == "__main__":
    main()
