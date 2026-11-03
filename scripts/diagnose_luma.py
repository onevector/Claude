"""One-off diagnostic: fingerprint Luma (luma.com) calendar pages before
writing a parser for them. Luma is known to be a Next.js app - check for
JSON-LD, __NEXT_DATA__ or other embedded JSON state, and fall back to
class-name heuristics if neither is present.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

URLS = [
    "https://luma.com/missionmatters",
    "https://luma.com/brandpopup",
]


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def inspect(url: str) -> None:
    section(url)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH ERROR: {exc}")
        return

    print(f"status={resp.status_code} length={len(resp.text)}")
    if resp.status_code != 200:
        print("BODY SNIPPET:", resp.text[:800].replace("\n", " "))
        return

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. JSON-LD
    ld_scripts = soup.find_all("script", type="application/ld+json")
    print(f"JSON-LD script count: {len(ld_scripts)}")
    for i, script in enumerate(ld_scripts[:3]):
        raw = script.string or script.get_text()
        print(f"-- JSON-LD #{i} (first 1500 chars) --")
        print((raw or "")[:1500])

    # 2. Next.js / embedded state blobs
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data:
        raw = next_data.string or next_data.get_text()
        print(f"\n__NEXT_DATA__ found, length={len(raw or '')}")
        try:
            data = json.loads(raw)
            print("Top-level keys:", list(data.keys()))
            # try to find anything event-ish recursively, shallow dump
            print(json.dumps(data, indent=2)[:3000])
        except Exception as exc:  # noqa: BLE001
            print(f"JSON parse error: {exc}")
            print(raw[:2000])
    else:
        print("\nNo __NEXT_DATA__ script found.")

    # other embedded JSON blobs worth checking
    for marker in ("window.__", "__APOLLO_STATE__", "__INITIAL_STATE__", "__remixContext", "self.__next_f"):
        if marker in html:
            idx = html.find(marker)
            print(f"\nmarker {marker!r} found at offset {idx}, snippet:")
            print(html[idx: idx + 500])

    # 3. generic class-name heuristic fallback
    from collections import Counter
    counter: Counter[str] = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            lc = cls.lower()
            if any(h in lc for h in ("event", "card", "listing", "item")):
                counter[cls] += 1
    top = counter.most_common(10)
    print(f"\ncandidate classes (event/card/listing/item): {top}")
    for cls, count in top[:5]:
        el = soup.find(class_=cls)
        print(f"\n-- class={cls!r} count={count} --")
        print(el.prettify()[:1000])

    # 4. links that look like individual event pages
    event_links = sorted({a["href"] for a in soup.find_all("a", href=True) if "/event" in a["href"].lower() or a["href"].count("/") <= 2})
    print(f"\nlinks (candidate event pages, first 20): {list(event_links)[:20]}")

    print(f"\ntotal <script> tags: {len(soup.find_all('script'))}")
    print(f"raw HTML first 1000 chars:\n{html[:1000]}")


def main() -> None:
    for url in URLS:
        try:
            inspect(url)
        except Exception as exc:  # noqa: BLE001
            print(f"\n{url} FAILED: {exc}")


if __name__ == "__main__":
    main()
