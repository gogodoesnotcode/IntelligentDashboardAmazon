# scraper/config.py

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

# Reviews: product page gives ~8 for free.
# We then try the dedicated review endpoint for extra pages.
# MAX_REVIEW_PAGES × ~10 reviews/page = up to 50 extra reviews per product.
# Total target: ~8 (product page) + 50 (review pages) = ~58 per product
#               × 10 products × 6 brands ≈ 3,480 reviews total
MAX_REVIEW_PAGES = 5

OUTPUT_DIR  = "data/raw"
PROFILE_DIR = "./browser_profile"

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