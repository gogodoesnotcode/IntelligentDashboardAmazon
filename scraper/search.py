# scraper/search.py
# Candidate ASIN discovery only — never trusted alone.
# Search-result markup does not confirm brand; that happens on the product
# page in product_page.py. This module's only job is: find ASINs, dedupe.

import logging

from config import CATEGORY_NODE, MAX_PAGES_SEARCH, DELAY_PAGE
from browser import sleep, scroll, is_blocked

log = logging.getLogger(__name__)


def get_brand_candidates(brand: str, page) -> list[str]:
    """Return deduplicated candidate ASINs for `brand`. No brand claim from
    this markup is trusted — every candidate must still be confirmed against
    the product page before it's written anywhere."""
    asins = []
    query = "+".join(brand.lower().split()) + "+luggage+bag"

    for page_num in range(1, MAX_PAGES_SEARCH + 1):
        url = f"https://www.amazon.in/s?k={query}&rh=n%3A{CATEGORY_NODE}&page={page_num}"
        log.info(f"  Search page {page_num}: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            # Playwright raises a non-Timeout error when a navigation triggers
            # a file download (e.g. an ad redirect) instead of loading HTML —
            # not worth failing the whole brand over, just stop paginating.
            log.warning(f"  Navigation failed on search page {page_num}: {e}")
            break
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
            asins.append(asin)
            page_asins += 1

        log.info(f"  {page_asins} candidate ASINs on page {page_num}")
        if page_asins == 0:
            break

    unique = list(dict.fromkeys(asins))
    log.info(f"  Total unique candidates for {brand}: {len(unique)}")
    return unique
