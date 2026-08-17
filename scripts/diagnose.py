"""One-off diagnostic: fingerprint each configured site's event-list markup
so CSS selectors can be added to config/sites.yaml without needing to fetch
the raw pages from a developer machine. Prints to stdout (visible in the
GitHub Actions job log); makes no repo changes.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

CONFIG_PATH = ROOT / "config" / "sites.yaml"
EVENTY_HINTS = ("event", "cal-item", "calendar-item", "listing", "agenda")
EXPORT_HINTS = ("ical", "ics", "rss", "subscribe", "export", "webcal")


def candidate_classes(soup: BeautifulSoup, min_count: int = 3, max_report: int = 6) -> list[str]:
    counter: Counter[str] = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if any(hint in cls.lower() for hint in EVENTY_HINTS):
                counter[cls] += 1
    return [cls for cls, count in counter.most_common(max_report) if count >= min_count]


def find_export_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    links = []
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").lower()
        href = a["href"].lower()
        if any(hint in text or hint in href for hint in EXPORT_HINTS):
            links.append((a.get_text(strip=True), a["href"]))
    return links


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    for site in config["sites"]:
        name = site["name"]
        url = site["url"]
        print(f"\n===== {name} ({url}) =====")
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        except Exception as exc:  # noqa: BLE001
            print(f"FETCH ERROR: {exc}")
            continue

        print(f"status={resp.status_code} length={len(resp.text)}")
        if resp.status_code != 200:
            print("BODY SNIPPET:", resp.text[:600].replace("\n", " "))
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        export_links = find_export_links(soup)
        if export_links:
            print("EXPORT/SUBSCRIBE LINKS:")
            for text, href in export_links[:10]:
                print(f"  - {text!r} -> {href}")

        classes = candidate_classes(soup)
        if not classes:
            print("No repeating event-like class names found via heuristic.")
        for cls in classes:
            elements = soup.find_all(class_=cls)
            print(f"\n-- class={cls!r} count={len(elements)} --")
            print(elements[0].prettify()[:1200])


if __name__ == "__main__":
    main()
