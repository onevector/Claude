"""Sixth-pass diagnostics, verifying the fetch_rendered_html fix (load
instead of networkidle) against ABALA, and checking Glue Up's actual org
events URL discovered in diagnose5.py.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import fetch_rendered_html  # noqa: E402

EVENTY_HINTS = ("event", "cal-item", "calendar-item", "listing", "agenda", "card")


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def candidate_classes(soup: BeautifulSoup, min_count: int = 2, max_report: int = 10) -> list[str]:
    counter: Counter[str] = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if any(hint in cls.lower() for hint in EVENTY_HINTS):
                counter[cls] += 1
    return [cls for cls, count in counter.most_common(max_report) if count >= min_count]


def abala_retry() -> None:
    section("ABALA: retry with 'load' wait strategy")
    html = fetch_rendered_html("https://www.abala.org/aba-events", wait_ms=5000)
    print(f"rendered length={len(html)}")
    soup = BeautifulSoup(html, "html.parser")

    iframes = soup.find_all("iframe")
    print(f"iframe count: {len(iframes)}")
    for f in iframes:
        print(f"  src={f.get('src')!r}")

    ld_json_events = 0
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        blob = json.dumps(data).lower()
        if '"@type": "event"' in blob or '"@type":"event"' in blob:
            ld_json_events += 1
    print(f"JSON-LD Event scripts: {ld_json_events}")

    classes = candidate_classes(soup)
    if not classes:
        print("No repeating event-like class names found.")
    for cls in classes:
        elements = soup.find_all(class_=cls)
        print(f"\n-- class={cls!r} count={len(elements)} --")
        print(elements[0].prettify()[:1000])


def glueup_org_events() -> None:
    section("Glue Up: /organization/813/events/")
    html = fetch_rendered_html("https://iercc.glueup.com/organization/813/events/", wait_ms=4000)
    print(f"rendered length={len(html)}")
    soup = BeautifulSoup(html, "html.parser")

    ld_json_events = 0
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        blob = json.dumps(data).lower()
        if '"@type": "event"' in blob or '"@type":"event"' in blob:
            ld_json_events += 1
    print(f"JSON-LD Event scripts: {ld_json_events}")

    classes = candidate_classes(soup)
    if not classes:
        print("No repeating event-like class names found.")
    for cls in classes:
        elements = soup.find_all(class_=cls)
        print(f"\n-- class={cls!r} count={len(elements)} --")
        print(elements[0].prettify()[:1200])

    event_links = [a["href"] for a in soup.find_all("a", href=True) if "/event/" in a["href"]]
    print(f"\nlinks matching /event/: {len(event_links)}")
    for href in event_links[:15]:
        print(f"  {href}")


def main() -> None:
    for fn in (abala_retry, glueup_org_events):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f"\n{fn.__name__} FAILED: {exc}")


if __name__ == "__main__":
    main()
