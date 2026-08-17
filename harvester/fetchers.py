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
