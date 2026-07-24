# scraper/product_page.py
# Scrapes the product detail page (PDP) and CONFIRMS brand from the byline /
# product-details table — never from a substring match on the title.
# This is the fix for the fail-open bug: an ASIN whose brand can't be
# positively confirmed is rejected, not kept.

import re
import time
import random
import logging
from datetime import datetime

from browser import PWTimeout, sleep, is_blocked, safe_text, clean_price, first_match
from config import DELAY_PAGE
from models import ProductRecord
from pydantic import ValidationError

log = logging.getLogger(__name__)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _confirm_brand(page, expected_brand: str) -> bool:
    """Confirm `expected_brand` against #bylineInfo, falling back to the
    product-details table's Brand row. Returns True only on a positive match."""
    expected_norm = _normalize(expected_brand)

    byline = safe_text(page, "#bylineInfo", timeout_ms=3000)
    if byline and expected_norm in _normalize(byline):
        return True

    for selector in (
        "#productDetails_techSpec_section_1 tr",
        "#productDetails_detailBullets_sections1 tr",
        "#detailBullets_feature_div li",
    ):
        for row in page.query_selector_all(selector):
            row_text = row.inner_text()
            if "brand" in row_text.lower() and expected_norm in _normalize(row_text):
                return True

    return False


def fetch_product(asin: str, brand: str, page) -> tuple[ProductRecord | None, str | None]:
    """Scrape and validate one product page.

    Returns (record, None) on success or (None, reason) on rejection —
    every rejection carries a reason so a bad run is visible without
    opening every CSV by hand.
    """
    url = f"https://www.amazon.in/dp/{asin}"
    log.info(f"  Product: {url}")

    try:
        page.goto(url, wait_until="networkidle", timeout=35000)
    except PWTimeout:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            return None, "timeout"

    sleep(DELAY_PAGE)

    if is_blocked(page):
        return None, "blocked"

    title = safe_text(page, "#productTitle", timeout_ms=8000)
    if not title:
        return None, "no_title"

    if not _confirm_brand(page, brand):
        return None, f"brand_unconfirmed: wanted={brand}"

    price = first_match(page, [
        ".a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen",
        "#priceblock_ourprice", "#priceblock_dealprice",
        ".a-price .a-offscreen", ".a-price-whole",
    ])
    mrp = first_match(page, [
        ".a-text-price .a-offscreen",
        "#priceblock_saleprice",
        ".basisPrice .a-offscreen",
    ])
    rating = first_match(page, [
        '[data-hook="rating-out-of-text"]',
        ".a-icon-alt", "#acrPopover .a-icon-alt",
    ])
    review_count = first_match(page, [
        '[data-hook="total-review-count"]',
        "#acrCustomerReviewText",
    ])

    price_num = clean_price(price)
    mrp_num = clean_price(mrp)
    discount = (
        round((mrp_num - price_num) / mrp_num * 100, 1)
        if price_num and mrp_num and mrp_num > price_num else None
    )

    def parse_float(s):
        m = re.search(r"([\d.]+)", s or "")
        return float(m.group(1)) if m else None

    def parse_int(s):
        m = re.search(r"[\d,]+", s or "")
        return int(m.group().replace(",", "")) if m else None

    # Scroll down to render the review section before caller scrapes reviews
    for anchor in ['#reviewsMedley', '#customerReviews', '#customer-reviews-content']:
        el = page.query_selector(anchor)
        if el:
            el.scroll_into_view_if_needed()
            time.sleep(random.uniform(1.5, 2.5))
            break
    for _ in range(4):
        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.uniform(0.8, 1.5))
    sleep((1.0, 2.0))

    try:
        record = ProductRecord(
            asin=asin,
            brand=brand,
            title=title,
            price=price_num,
            mrp=mrp_num,
            discount_pct=discount,
            rating=parse_float(rating),
            review_count=parse_int(review_count),
            scraped_at=datetime.now().isoformat(timespec="seconds"),
        )
    except ValidationError as e:
        return None, f"validation_error: {e}"

    return record, None
