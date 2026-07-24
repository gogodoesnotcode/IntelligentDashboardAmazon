# scraper/config.py

from pathlib import Path

_SCRAPER_DIR = Path(__file__).resolve().parent

BRANDS = [
    "Safari",
    "American Tourister",
    "VIP",
    "Skybags",
    "Aristocrat",
    "Nasher Miles",
]

CATEGORY_NODE    = "1984443031"   # Amazon India: Luggage & Bags
MAX_PAGES_SEARCH = 3              # search result pages per brand
MAX_ASINS        = 10             # max products per brand

# Reviews: product page gives ~8 for free, already enough to clear the
# 50+ reviews/brand target at 10 products/brand. The paginated
# /product-reviews/{asin} endpoint is enrichment, not a requirement —
# it blocks quickly and shouldn't be allowed to eat retries meant for
# products that matter more. See SCRAPING_APPROACH_UPDATE.md.
MIN_REVIEWS_PER_PRODUCT_PAGE = 6   # sanity floor — log a warning (don't fail
                                    # the run) if a product page renders fewer
REVIEW_PAGINATION_ENABLED = True   # flip off entirely per-brand via circuit breaker
MAX_REVIEW_PAGES = 2                # down from 5 — diminishing returns once
                                     # product-page reviews cover the target
MIN_REVIEW_TEXT_LEN = 15            # reviews shorter than this ("Good product")
                                     # are counted but flagged, not silently kept

# Resolved relative to this file so OUTPUT_DIR is correct regardless of cwd —
# always scraper/raw/, the single raw-data directory agent/ reads from.
OUTPUT_DIR  = str(_SCRAPER_DIR / "raw")
PROFILE_DIR = str(_SCRAPER_DIR.parent / "browser_profile")

# Flip to False on the very first run to seed cookies manually,
# then set back to True for all subsequent runs.
HEADLESS = True

# Delay ranges in seconds — keep generous to avoid blocks
DELAY_PAGE          = (3.0, 6.0)
DELAY_REVIEW_PAGE   = (4.0, 8.0)   # slightly longer for the blocked endpoint
DELAY_PRODUCT       = (5.0, 10.0)
DELAY_BRAND         = (10.0, 20.0)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]