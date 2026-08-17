"""Third-pass diagnostics:
- Irwindale: now fetchable (UA fix) - what's its actual event markup?
- ABAIE: only 2 of ~10 candidate events parsed successfully - dump every
  (title, date_text, time_text) triple and whether it parsed, to find
  which format is tripping up dateutil.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

EVENTY_HINTS = ("event", "cal-item", "calendar-item", "listing", "agenda", "day-cell", "fc-")


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def irwindale_structure() -> None:
    section("Irwindale: event markup now that UA fix works")
    url = "https://www.irwindalechamber.org/test-calendar"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
    print(f"status={resp.status_code} length={len(resp.text)}")
    soup = BeautifulSoup(resp.text, "html.parser")

    counter: Counter[str] = Counter()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if any(hint in cls.lower() for hint in EVENTY_HINTS):
                counter[cls] += 1
    top = counter.most_common(10)
    print(f"candidate classes: {top}")
    for cls, count in top[:6]:
        el = soup.find(class_=cls)
        print(f"\n-- class={cls!r} count={count} --")
        print(el.prettify()[:1200])

    # also check for JSON blobs (in case it's JS-rendered) and any <script>
    # with obviously event-ish JSON
    scripts = soup.find_all("script")
    print(f"\ntotal <script> tags: {len(scripts)}")
    for s in scripts:
        if s.string and ("event" in s.string.lower()) and len(s.string) < 5000:
            print("---inline script mentioning 'event'---")
            print(s.string[:800])


def abaie_full_debug() -> None:
    section("ABAIE: per-item date/time parse debug")
    resp = requests.get("https://abaie.org/events", headers=DEFAULT_HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    links = soup.select(".eventDetailsLink")
    start_dates = soup.select(".eventInfoStartDate")
    start_times = soup.select(".eventInfoStartTime")
    print(f"counts: links={len(links)} dates={len(start_dates)} times={len(start_times)}")

    for i, (link, date_el, time_el) in enumerate(zip(links, start_dates, start_times)):
        title = link.get_text(" ", strip=True)
        date_text = date_el.get_text(" ", strip=True).removeprefix("Start").strip()
        time_text = time_el.get_text(" ", strip=True).strip()
        combined = f"{date_text} {time_text}".strip()
        try:
            parsed = dateparser.parse(combined)
            status = f"OK -> {parsed.isoformat()}"
        except Exception as exc:  # noqa: BLE001
            status = f"FAIL -> {exc}"
        print(f"[{i}] title={title!r} date_text={date_text!r} time_text={time_text!r} :: {status}")


def main() -> None:
    irwindale_structure()
    abaie_full_debug()


if __name__ == "__main__":
    main()
