# scraper/browser.py
# Low-level Playwright helpers shared by search.py, product_page.py, reviews.py.
# Nothing here knows about brands or CSVs — it only knows how to drive a page.

import re
import time
import random
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

from config import PROFILE_DIR, HEADLESS, USER_AGENTS

log = logging.getLogger(__name__)


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


def first_match(page, selectors: list[str]) -> str | None:
    for sel in selectors:
        val = safe_text(page, sel, timeout_ms=2000)
        if val:
            return val
    return None


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


def launch_context(playwright):
    """Launch a persistent, stealth-applied browser context + page, ready to scrape."""
    context = playwright.chromium.launch_persistent_context(
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
    return context, page


__all__ = [
    "sync_playwright", "PWTimeout",
    "sleep", "is_blocked", "safe_text", "clean_price", "scroll",
    "first_match", "warm_up_session", "launch_context",
]
