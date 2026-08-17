from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..fetchers import fetch_html

# GrowthZone/ChamberMaster calendar grid pages (.gz-cal-event) only list
# title + a link to the event's detail page; date/time/location live on
# that detail page under .gz-event-date / .gz-event-location, e.g.
# "Date and Time Wednesday Aug 5, 2026 9:00 AM - 10:15 AM PDT".
DATE_RANGE_RE = re.compile(
    r"(?P<date>[A-Za-z]+ [A-Za-z]+ \d{1,2}, \d{4})\s+"
    r"(?P<start>\d{1,2}:\d{2}\s*[AaPp][Mm])\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*[AaPp][Mm])"
)
LOCATION_LABEL_RE = re.compile(r"^Location\s*")


def extract_chambermaster_events(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    seen_urls: set[str] = set()
    stubs: list[tuple[str, str]] = []
    for link in soup.select(".gz-cal-event a[href]"):
        href = urljoin(source_url, link["href"]).split("?")[0]
        if href in seen_urls:
            continue
        title = link.get_text(" ", strip=True)
        if not title:
            continue
        seen_urls.add(href)
        stubs.append((title, href))

    events: list[dict[str, Any]] = []
    for title, detail_url in stubs:
        try:
            detail_html = fetch_html(detail_url)
        except Exception:  # noqa: BLE001 - one bad event shouldn't sink the site
            continue

        detail_soup = BeautifulSoup(detail_html, "html.parser")
        date_el = detail_soup.select_one(".gz-event-date")
        if date_el is None:
            continue

        match = DATE_RANGE_RE.search(date_el.get_text(" ", strip=True))
        if not match:
            continue
        try:
            start = dateparser.parse(f"{match['date']} {match['start']}")
            end = dateparser.parse(f"{match['date']} {match['end']}")
        except (ValueError, TypeError, OverflowError):
            continue

        location = None
        loc_el = detail_soup.select_one(".gz-event-location")
        if loc_el is not None:
            location = LOCATION_LABEL_RE.sub("", loc_el.get_text(" ", strip=True)).strip() or None

        events.append(
            {
                "title": title,
                "start": start,
                "end": end,
                "all_day": False,
                "location": location,
                "description": None,
                "url": detail_url,
            }
        )

    return events
