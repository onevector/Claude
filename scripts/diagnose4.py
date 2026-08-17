"""Fourth-pass diagnostics: render JS-dependent pages with Playwright and
fingerprint their event markup, same heuristic as diagnose.py but on
rendered HTML instead of the raw (JS-free) response:
- Irwindale: calendar is a JS-loaded widget referencing chamberorganizer.com
- ABALA: confirmed Wix SPA, zero server-rendered content
- Glue Up (iercc.glueup.com): Inland Empire Chamber's actual full calendar
  platform, external to iechamber.org
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


def candidate_classes(soup: BeautifulSoup, min_count: int = 2, max_report: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if any(hint in cls.lower() for hint in EVENTY_HINTS):
                counter[cls] += 1
    return [cls for cls, count in counter.most_common(max_report) if count >= min_count]


def inspect(url: str, wait_ms: int = 3000) -> None:
    section(url)
    try:
        html = fetch_rendered_html(url, wait_ms=wait_ms)
    except Exception as exc:  # noqa: BLE001
        print(f"RENDER ERROR: {exc}")
        return

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
    print(f"JSON-LD scripts containing an Event type: {ld_json_events}")

    classes = candidate_classes(soup)
    if not classes:
        print("No repeating event-like class names found via heuristic.")
    for cls in classes:
        elements = soup.find_all(class_=cls)
        print(f"\n-- class={cls!r} count={len(elements)} --")
        print(elements[0].prettify()[:1000])


def main() -> None:
    inspect("https://www.irwindalechamber.org/test-calendar")
    inspect("https://www.abala.org/aba-events")
    inspect("https://iercc.glueup.com/")


if __name__ == "__main__":
    main()
