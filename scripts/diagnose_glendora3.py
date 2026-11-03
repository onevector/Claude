"""Diagnose Glendora's new 403: check response headers/body for WAF
fingerprints (Cloudflare/Akamai/Sucuri/etc), and whether a different UA or
a brief delay changes the outcome.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

URL = "https://business.glendora-chamber.org/events"

UA_VARIANTS = {
    "current (Chrome 128 UA)": DEFAULT_HEADERS,
    "Chrome 131 UA": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },
    "Safari macOS UA": {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },
    "no User-Agent at all": {},
}


def attempt(label: str, headers: dict, url: str = URL) -> None:
    try:
        resp = requests.get(url, headers=headers, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}] ERROR: {exc}")
        return
    print(f"[{label}] status={resp.status_code} length={len(resp.text)}")
    print(f"[{label}] response headers: {dict(resp.headers)}")
    if resp.status_code != 200:
        print(f"[{label}] BODY (first 1500 chars):\n{resp.text[:1500]}")


def main() -> None:
    for label, headers in UA_VARIANTS.items():
        attempt(label, headers)
        print()

    print("Retrying original request after a 5s delay (rule out instant rate-limit)...")
    time.sleep(5)
    attempt("current (Chrome 128 UA) - retry after delay", DEFAULT_HEADERS)

    print("\nChecking homepage and a couple of other paths on the same domain:")
    for path in ("/", "/events/", "/communitycalendar"):
        full_url = f"https://business.glendora-chamber.org{path}"
        attempt(path, DEFAULT_HEADERS, url=full_url)


if __name__ == "__main__":
    main()
