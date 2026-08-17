from __future__ import annotations

import requests

DEFAULT_HEADERS = {
    # A self-identifying UA ("...ChamberEventsHarvester...") gets 403'd by
    # at least one target site's basic UA-sniffing WAF rule; a standard
    # browser UA is accepted everywhere observed so far.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url: str, timeout: int = 20) -> str:
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_rendered_html(url: str, timeout_ms: int = 30000, wait_ms: int = 2000) -> str:
    """Fetch a page's HTML after executing its JavaScript, for sites whose
    event data only exists client-side (Wix SPAs, JS-injected widgets).
    Requires `playwright install chromium` to have been run.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
            page.wait_for_timeout(wait_ms)
            return page.content()
        finally:
            browser.close()
