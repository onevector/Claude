from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

# Inland Empire Chamber's /events page embeds a Glue Up-powered event list
# directly (.event-row), which is richer than the single data:text/calendar
# link elsewhere on the page (harvester/parsers/ics_links.py): it has a
# venue name and a real per-event Glue Up URL for every listed event, e.g.
#   .event-listing-title  -> title text + href (real event page, signup CTA)
#   .event-date            -> "03 Oct 2026 | 04:00 PM - 08:00 PM"
#   .event-venue            -> "Toyota Arena"
# The title link's text also contains a visually-hidden duplicate ("...
# (opens in a new window)") that must be stripped before use.


def extract_iechamber_events(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict[str, Any]] = []

    for row in soup.select(".event-row"):
        title_el = row.select_one(".event-listing-title")
        date_el = row.select_one(".event-date")
        venue_el = row.select_one(".event-venue")
        if title_el is None or date_el is None:
            continue

        for hidden in title_el.select(".visually-hidden, .sr-only"):
            hidden.decompose()
        title = title_el.get_text(" ", strip=True)
        href = title_el.get("href")
        if not title or not href:
            continue
        url = urljoin(source_url, href)

        date_text = date_el.get_text(" ", strip=True)
        day_part, _, time_part = date_text.partition("|")
        start_time_text, _, end_time_text = time_part.partition("-")
        try:
            start = dateparser.parse(f"{day_part.strip()} {start_time_text.strip()}")
            end = (
                dateparser.parse(f"{day_part.strip()} {end_time_text.strip()}")
                if end_time_text.strip()
                else None
            )
        except (ValueError, TypeError, OverflowError):
            continue

        events.append(
            {
                "title": title,
                "start": start,
                "end": end,
                "all_day": not time_part.strip(),
                "location": venue_el.get_text(" ", strip=True) if venue_el else None,
                "description": None,
                "url": url,
            }
        )

    return events
