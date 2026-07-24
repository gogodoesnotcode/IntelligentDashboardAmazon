# scraper/reviews.py
# Review extraction. Logic is mostly unchanged from the original scraper —
# only the output now passes through ReviewRecord for validation.

import re
import logging
from datetime import datetime

from browser import PWTimeout, sleep, is_blocked
from config import DELAY_REVIEW_PAGE, MAX_REVIEW_PAGES, REVIEW_PAGINATION_ENABLED, MIN_REVIEWS_PER_PRODUCT_PAGE
from models import ReviewRecord
from pydantic import ValidationError

log = logging.getLogger(__name__)


def _parse_reviews_from_page(page, asin: str, seen: set) -> list[ReviewRecord]:
    """Extract review records from whatever review divs are currently rendered.
    `seen` is a shared set of review texts — used to deduplicate across the
    product page and all subsequent review endpoint pages."""
    reviews = []

    for selector in ['[data-hook="review"]', '.review']:
        for div in page.query_selector_all(selector):
            text_el = (
                div.query_selector('[data-hook="reviewText"]') or
                div.query_selector('[data-hook="review-body"] span') or
                div.query_selector('.review-text-content span') or
                div.query_selector('[data-hook="review-body"]')
            )
            text = text_el.inner_text().strip() if text_el else ""
            if not text or text in seen:
                continue
            seen.add(text)

            stars_el = (
                div.query_selector('[data-hook="review-star-rating"]') or
                div.query_selector('[data-hook="cmps-review-star-rating"]')
            )
            stars_raw = stars_el.inner_text().strip() if stars_el else ""
            m = re.search(r"([\d.]+)", stars_raw)
            stars = float(m.group(1)) if m else None

            date_el = div.query_selector('[data-hook="review-date"]')
            date_raw = date_el.inner_text().strip() if date_el else ""
            m = re.search(r"(\d+\s+\w+\s+\d{4})", date_raw)
            date = m.group(1) if m else date_raw

            title_el = (
                div.query_selector('[data-hook="reviewTitle"]') or
                div.query_selector('[data-hook="review-title"] span')
            )
            verified_el = div.query_selector('[data-hook="avp-badge"]')
            helpful_el = div.query_selector('[data-hook="helpful-vote-statement"]')

            try:
                reviews.append(ReviewRecord(
                    asin=asin,
                    stars=stars,
                    title=title_el.inner_text().strip() if title_el else "",
                    text=text,
                    date=date,
                    verified=verified_el is not None,
                    helpful=helpful_el.inner_text().strip() if helpful_el else "",
                    scraped_at=datetime.now().isoformat(timespec="seconds"),
                ))
            except ValidationError as e:
                log.warning(f"    Dropped malformed review for {asin}: {e}")

    return reviews


def _scrape_review_pages(asin: str, page, seen: set, pagination_state: dict) -> list[ReviewRecord]:
    """Hit the /product-reviews/ endpoint for up to MAX_REVIEW_PAGES pages.
    This endpoint is often CAPTCHA-protected; we stop at the first block,
    flip the shared circuit breaker so the rest of this brand's ASINs skip
    pagination entirely, and return however many reviews we collected."""
    reviews = []

    for page_num in range(1, MAX_REVIEW_PAGES + 1):
        url = (
            f"https://www.amazon.in/product-reviews/{asin}"
            f"?ie=UTF8&reviewerType=all_reviews&sortBy=recent&pageNumber={page_num}"
        )
        log.info(f"    Review page {page_num}/{MAX_REVIEW_PAGES}: {asin}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
        except PWTimeout:
            log.warning(f"    Timeout on review page {page_num}")
            break

        sleep(DELAY_REVIEW_PAGE)

        if is_blocked(page):
            log.warning(f"    Blocked on review page {page_num} — stopping")
            pagination_state["blocked"] = True
            break

        page_reviews = _parse_reviews_from_page(page, asin, seen)
        reviews.extend(page_reviews)
        log.info(f"    +{len(page_reviews)} reviews (total extra so far: {len(reviews)})")

        if len(page_reviews) < 8:
            break

        sleep((1.5, 3.0))

    return reviews


def fetch_reviews_for_asin(asin: str, page, pagination_state: dict) -> list[ReviewRecord]:
    """Scrape reviews already rendered on the current product page, then
    page through the dedicated review endpoint for more — unless the
    endpoint has already blocked once for this brand's run, per the
    circuit breaker in `pagination_state` (shared across a brand's ASINs)."""
    seen: set = set()
    reviews = _parse_reviews_from_page(page, asin, seen)
    log.info(f"  Product page reviews: {len(reviews)}")
    if len(reviews) < MIN_REVIEWS_PER_PRODUCT_PAGE:
        log.warning(
            f"    {asin}: only {len(reviews)} reviews rendered on product page "
            f"(floor: {MIN_REVIEWS_PER_PRODUCT_PAGE})"
        )

    if REVIEW_PAGINATION_ENABLED and not pagination_state.get("blocked"):
        extra = _scrape_review_pages(asin, page, seen, pagination_state)
        if pagination_state.get("blocked"):
            log.warning(f"    Pagination blocked at {asin}, skipping pagination for remaining products in this brand")
        reviews.extend(extra)

    return reviews
