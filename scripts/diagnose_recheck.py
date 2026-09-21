"""Follow-up: (1) find Glendora's new calendar URL since the old one now
404s, and sanity-check Monrovia/Ontario on the same platform still work.
(2) get more of Inland Empire Chamber's new .event-row structure - check
all 3 events for an organizer field, and confirm the date format.
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def fetch(url: str):
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        print(f"{url}: status={resp.status_code} length={len(resp.text)}")
        return resp
    except Exception as exc:  # noqa: BLE001
        print(f"{url}: ERROR {exc}")
        return None


def glendora_recheck() -> None:
    section("Glendora: find working calendar URL")
    for url in (
        "https://business.glendora-chamber.org/events/calendarcatgid/6",
        "https://business.glendora-chamber.org/events/calendar/",
        "https://business.glendora-chamber.org/events/calendar",
        "https://business.glendora-chamber.org/events/",
        "https://business.glendora-chamber.org/",
    ):
        resp = fetch(url)
        if resp is not None and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cal_links = [a["href"] for a in soup.find_all("a", href=True) if "calendar" in a["href"].lower() or "events" in a["href"].lower()]
            uniq = sorted(set(cal_links))[:15]
            print(f"  candidate links: {uniq}")


def chambermaster_siblings_recheck() -> None:
    section("Monrovia / Ontario: still working?")
    for url in (
        "https://www.monroviacc.com/events/calendar/",
        "https://ontarioca.chambermaster.com/events/calendar/",
    ):
        resp = fetch(url)
        if resp is not None and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            count = len(soup.select(".gz-cal-event"))
            print(f"  .gz-cal-event count={count}")


def iechamber_full_rows() -> None:
    section("Inland Empire Chamber: full event-row dump (all 3)")
    resp = fetch("https://www.iechamber.org/events")
    if resp is None or resp.status_code != 200:
        return
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select(".event-row")
    print(f"event-row count: {len(rows)}")
    for i, row in enumerate(rows):
        title_el = row.select_one(".event-listing-title")
        date_el = row.select_one(".event-date")
        venue_el = row.select_one(".event-venue")
        print(f"\n--- row {i} ---")
        print(f"title={title_el.get_text(' ', strip=True) if title_el else None!r}")
        print(f"href={title_el.get('href') if title_el else None!r}")
        print(f"date={date_el.get_text(' ', strip=True) if date_el else None!r}")
        print(f"venue={venue_el.get_text(' ', strip=True) if venue_el else None!r}")
        # dump the whole row's text to eyeball anything else (organizer, price, etc.)
        print(f"full row text: {row.get_text(' | ', strip=True)[:500]!r}")


def main() -> None:
    for fn in (glendora_recheck, chambermaster_siblings_recheck, iechamber_full_rows):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f"\n{fn.__name__} FAILED: {exc}")


if __name__ == "__main__":
    main()
