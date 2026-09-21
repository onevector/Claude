from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..fetchers import fetch_html

# GrowthZone/ChamberMaster hosts at least two live template generations:
#
# OLD (Monrovia, Ontario as of 2026-09): calendar-grid list items
# (.gz-cal-event) with just title + link; date/time/location live on the
# detail page under .gz-event-date / .gz-event-location, e.g.
# "Date and Time Wednesday Aug 5, 2026 9:00 AM - 10:15 AM PDT".
#
# NEW (Glendora migrated to this at some point after 2026-08): card-based
# listing (.gz-events-card-body) with title/url/description already on the
# listing page via itemprop microdata (name/url/startDate/endDate) - no
# extra fetch needed for those. Location is still only on the detail page,
# in an unlabeled combined blob (.gz-card-datetime) that also repeats the
# date/time text, so it's extracted by stripping the date portion out.
DATE_RANGE_RE = re.compile(
    r"(?P<date>[A-Za-z]+ [A-Za-z]+ \d{1,2}, \d{4})\s+"
    r"(?P<start>\d{1,2}:\d{2}\s*[AaPp][Mm])\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*[AaPp][Mm])"
)
LOCATION_LABEL_RE = re.compile(r"^Location\s*")
WEEKDAY_DATE_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}"
)


def extract_chambermaster_events(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    if soup.select(".gz-cal-event"):
        return _extract_old_template(soup, source_url)
    if soup.select(".gz-events-card-body"):
        return _extract_new_template(soup, source_url)
    return []


def _dedupe_urls(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out = []
    for title, url in pairs:
        if url in seen or not title:
            continue
        seen.add(url)
        out.append((title, url))
    return out


def _extract_old_template(soup: BeautifulSoup, source_url: str) -> list[dict[str, Any]]:
    stubs = _dedupe_urls(
        [
            (link.get_text(" ", strip=True), urljoin(source_url, link["href"]).split("?")[0])
            for link in soup.select(".gz-cal-event a[href]")
        ]
    )

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


def _extract_new_template(soup: BeautifulSoup, source_url: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for card in soup.select(".gz-events-card-body"):
        title_el = card.select_one("a.gz-card-title, a.gz-event-card-title, [itemprop='url']")
        if title_el is None or not title_el.get("href"):
            continue
        title = title_el.get_text(" ", strip=True)
        detail_url = urljoin(source_url, title_el["href"]).split("?")[0]
        if not title:
            continue

        start_meta = card.select_one("meta[itemprop='startDate']")
        end_meta = card.select_one("meta[itemprop='endDate']")
        if start_meta is None or not start_meta.get("content"):
            continue
        try:
            start = dateparser.parse(start_meta["content"])
        except (ValueError, TypeError, OverflowError):
            continue
        end = None
        if end_meta is not None and end_meta.get("content"):
            try:
                end = dateparser.parse(end_meta["content"])
            except (ValueError, TypeError, OverflowError):
                end = None

        description_el = card.select_one(".gz-events-description")
        description = description_el.get_text(" ", strip=True) if description_el else None

        events.append(
            {
                "title": title,
                "start": start,
                "end": end,
                "all_day": False,
                "location": _new_template_location(detail_url),
                "description": description,
                "url": detail_url,
            }
        )

    return events


def _new_template_location(detail_url: str) -> str | None:
    try:
        detail_html = fetch_html(detail_url)
    except Exception:  # noqa: BLE001 - a missing location shouldn't sink the event
        return None
    detail_soup = BeautifulSoup(detail_html, "html.parser")

    # .gz-card-datetime is an unlabeled blob mixing venue/address with the
    # date/time text again, e.g. "Glendora Village 224 N. Glendora Ave.
    # ... Wednesday, September 23, 2026 (5:00 PM - 9:00 PM) ( PDT ) ...".
    # The venue/address is whatever precedes the weekday-date pattern.
    blob_el = detail_soup.select_one(".gz-card-datetime")
    if blob_el is not None:
        text = blob_el.get_text(" ", strip=True)
        match = WEEKDAY_DATE_RE.search(text)
        location = text[: match.start()].strip() if match else text.strip()
        if location:
            return location

    fallback_el = detail_soup.select_one(".gz-location-description")
    if fallback_el is not None:
        text = fallback_el.get_text(" ", strip=True)
        return text or None

    return None
