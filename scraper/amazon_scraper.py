# scraper/amazon_scraper.py

import os
import re
import time
import random
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

import pandas as pd
from config import (
    BRANDS, CATEGORY_NODE, MAX_PAGES_SEARCH, MAX_ASINS, MAX_REVIEW_PAGES,
    OUTPUT_DIR, PROFILE_DIR, HEADLESS,
    DELAY_PAGE, DELAY_REVIEW_PAGE, DELAY_PRODUCT, DELAY_BRAND, USER_AGENTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def sleep(range_: tuple):
    time.sleep(random.uniform(*range_))


def is_blocked(page) -> bool:
    url = page.url.lower()
    if any(k in url for k in ("captcha", "validatecaptcha", "signin", "ap/signin")):
        return True
    return any(page.query_selector(s) for s in [
        'form[action*="/errors/validateCaptcha"]',
        '#captchacharacters',
        'input[name="email"]',
    ])


def safe_text(page, selector: str, timeout_ms: int = 4000) -> str | None:
    try:
        page.wait_for_selector(selector, timeout=timeout_ms)
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else None
    except PWTimeout:
        return None


def clean_price(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(re.sub(r"[^\d.]", "", s.replace(",", "")))
    except ValueError:
        return None


def scroll(page, passes: int = 3):
    for _ in range(passes):
        page.mouse.wheel(0, random.randint(300, 800))
        time.sleep(random.uniform(0.5, 1.2))


def _first_match(page, selectors: list[str]) -> str | None:
    for sel in selectors:
        val = safe_text(page, sel, timeout_ms=2000)
        if val:
            return val
    return None


def _parse_reviews_from_page(page, asin: str, seen: set) -> list[dict]:
    """
    Extract review dicts from whatever review divs are currently rendered.
    `seen` is a shared set of review texts — used to deduplicate across
    the product page and all subsequent review endpoint pages.
    """
    reviews = []

    for selector in ['[data-hook="review"]', '.review']:
        for div in page.query_selector_all(selector):
            text_el = (
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

            date_el  = div.query_selector('[data-hook="review-date"]')
            date_raw = date_el.inner_text().strip() if date_el else ""
            m        = re.search(r"(\d+\s+\w+\s+\d{4})", date_raw)
            date     = m.group(1) if m else date_raw

            title_el    = div.query_selector('[data-hook="review-title"] span')
            verified_el = div.query_selector('[data-hook="avp-badge"]')
            helpful_el  = div.query_selector('[data-hook="helpful-vote-statement"]')

            reviews.append({
                "asin":       asin,
                "stars":      stars,
                "title":      title_el.inner_text().strip() if title_el else "",
                "text":       text,
                "date":       date,
                "verified":   verified_el is not None,
                "helpful":    helpful_el.inner_text().strip() if helpful_el else "",
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
            })

    return reviews


# ── Session warm-up ────────────────────────────────────────────────────────────

def warm_up_session(page):
    log.info("Warming up session...")
    page.goto("https://www.amazon.in", wait_until="domcontentloaded")
    sleep((3, 5))
    scroll(page)
    box = page.query_selector('#twotabsearchtextbox')
    if box:
        box.click()
        time.sleep(random.uniform(0.5, 1.0))
        box.type("luggage bags", delay=random.randint(60, 120))
        time.sleep(random.uniform(0.8, 1.5))
        page.keyboard.press("Escape")
    sleep((2, 3))


# ── Step 1: collect ASINs from search results ──────────────────────────────────

def get_brand_asins(brand: str, page) -> list[str]:
    asins = []
    first_word = brand.lower().split()[0]
    query = "+".join(brand.lower().split()) + "+luggage+bag"

    for page_num in range(1, MAX_PAGES_SEARCH + 1):
        url = f"https://www.amazon.in/s?k={query}&rh=n%3A{CATEGORY_NODE}&page={page_num}"
        log.info(f"  Search page {page_num}: {url}")
        page.goto(url, wait_until="domcontentloaded")
        sleep(DELAY_PAGE)
        scroll(page)

        if is_blocked(page):
            log.warning(f"  Blocked on search page {page_num}")
            break

        page_asins = 0
        for card in page.query_selector_all('[data-asin]'):
            asin = card.get_attribute("data-asin")
            if not asin or len(asin) != 10:
                continue
            if card.query_selector('.puis-sponsored-label-text, [aria-label*="Sponsored"]'):
                continue
            title_el = card.query_selector("h2 span")
            if title_el and first_word not in title_el.inner_text().lower():
                continue
            asins.append(asin)
            page_asins += 1

        log.info(f"  {page_asins} ASINs on page {page_num}")
        if page_asins == 0:
            break

    unique = list(dict.fromkeys(asins))
    log.info(f"  Total unique ASINs for {brand}: {len(unique)}")
    return unique


# ── Step 2: scrape product page (metadata + first batch of reviews) ────────────

def scrape_product_and_reviews(asin: str, brand: str, page) -> tuple[dict | None, list[dict]]:
    url = f"https://www.amazon.in/dp/{asin}"
    log.info(f"  Product: {url}")

    try:
        page.goto(url, wait_until="networkidle", timeout=35000)
    except PWTimeout:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            log.error(f"  Page load failed: {asin}")
            return None, []

    sleep(DELAY_PAGE)

    if is_blocked(page):
        log.warning(f"  Blocked: {asin}")
        return None, []

    title = safe_text(page, "#productTitle", timeout_ms=8000)
    if not title:
        log.warning(f"  No title: {asin}")
        return None, []

    price = _first_match(page, [
        ".a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen",
        "#priceblock_ourprice", "#priceblock_dealprice",
        ".a-price .a-offscreen", ".a-price-whole",
    ])
    mrp = _first_match(page, [
        ".a-text-price .a-offscreen",
        "#priceblock_saleprice",
        ".basisPrice .a-offscreen",
    ])
    rating = _first_match(page, [
        '[data-hook="rating-out-of-text"]',
        ".a-icon-alt", "#acrPopover .a-icon-alt",
    ])
    review_count = _first_match(page, [
        '[data-hook="total-review-count"]',
        "#acrCustomerReviewText",
    ])

    price_num = clean_price(price)
    mrp_num   = clean_price(mrp)
    discount  = (
        round((mrp_num - price_num) / mrp_num * 100, 1)
        if price_num and mrp_num and mrp_num > price_num else None
    )

    def parse_float(s):
        m = re.search(r"([\d.]+)", s or "")
        return float(m.group(1)) if m else None

    def parse_int(s):
        m = re.search(r"[\d,]+", s or "")
        return int(m.group().replace(",", "")) if m else None

    product = {
        "asin":         asin,
        "brand":        brand,
        "title":        title,
        "price":        price_num,
        "mrp":          mrp_num,
        "discount_pct": discount,
        "rating":       parse_float(rating),
        "review_count": parse_int(review_count),
        "scraped_at":   datetime.now().isoformat(timespec="seconds"),
    }

    # Scroll down to render the review section, then scrape what's visible
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

    seen = set()
    reviews = _parse_reviews_from_page(page, asin, seen)
    log.info(f"  Product page reviews: {len(reviews)}")

    # Step 3: try the dedicated review endpoint for additional pages
    extra = _scrape_review_pages(asin, page, seen)
    reviews.extend(extra)

    return product, reviews


# ── Step 3: paginated review endpoint (best-effort, falls back silently) ────────

def _scrape_review_pages(asin: str, page, seen: set) -> list[dict]:
    """
    Hit the /product-reviews/ endpoint for up to MAX_REVIEW_PAGES pages.
    This endpoint is often CAPTCHA-protected; we stop at the first block
    and return however many reviews we managed to collect.
    The `seen` set is shared with the product page so there's no duplication.
    """
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
            break

        page_reviews = _parse_reviews_from_page(page, asin, seen)
        reviews.extend(page_reviews)
        log.info(f"    +{len(page_reviews)} reviews (total extra so far: {len(reviews)})")

        # Fewer than 8 reviews means we've hit the last page
        if len(page_reviews) < 8:
            break

        sleep((1.5, 3.0))

    return reviews


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROFILE_DIR, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            viewport={"width": 1280, "height": 800},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = context.new_page()
        if HAS_STEALTH:
            Stealth().apply_stealth_sync(page)
        page.set_extra_http_headers({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-IN,en;q=0.9",
        })

        warm_up_session(page)
        summary = []

        for brand in BRANDS:
            log.info(f"\n{'─'*45}\nBrand: {brand}\n{'─'*45}")

            asins = get_brand_asins(brand, page)[:MAX_ASINS]
            if not asins:
                log.warning(f"No ASINs found for {brand}")
                continue

            products, all_reviews = [], []

            for i, asin in enumerate(asins, 1):
                log.info(f"[{i}/{len(asins)}] {asin}")
                try:
                    prod, reviews = scrape_product_and_reviews(asin, brand, page)
                except Exception as e:
                    log.error(f"  Error: {e}")
                    prod, reviews = None, []

                if prod:
                    products.append(prod)
                    all_reviews.extend(reviews)
                    log.info(
                        f"  {prod['title'][:60]}...\n"
                        f"  ₹{prod['price']} | MRP ₹{prod['mrp']} | "
                        f"{prod['discount_pct']}% off | {prod['rating']}★ | "
                        f"{len(reviews)} reviews scraped"
                    )

                sleep(DELAY_PRODUCT)

            slug = brand.lower().replace(" ", "_")
            pd.DataFrame(products).to_csv(
                f"{OUTPUT_DIR}/{slug}_products.csv", index=False, encoding="utf-8-sig"
            )
            pd.DataFrame(all_reviews).to_csv(
                f"{OUTPUT_DIR}/{slug}_reviews.csv", index=False, encoding="utf-8-sig"
            )
            log.info(f"Saved {len(products)} products, {len(all_reviews)} reviews → {OUTPUT_DIR}/{slug}_*.csv")
            summary.append({"brand": brand, "products": len(products), "reviews": len(all_reviews)})

            sleep(DELAY_BRAND)

        context.close()

    log.info(f"\n{'='*45}\nSCRAPE COMPLETE\n{'='*45}")
    for row in summary:
        log.info(f"  {row['brand']:<22} {row['products']:>3} products  {row['reviews']:>4} reviews")


if __name__ == "__main__":
    main()