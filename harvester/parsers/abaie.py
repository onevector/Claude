from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

# ABAIE's upcoming-events widget renders three parallel lists
# (.eventDetailsLink, .eventInfoStartDate, .eventInfoStartTime) that are
# not nested under a shared container in the DOM, but all come from the
# same ASP.NET Repeater ("UpcomingEventsRepeater") bound to one ordered
# data source, so pairing them by position is reliable as long as the
# three lists have equal length (guarded below).


def extract_abaie_events(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    links = soup.select(".eventDetailsLink")
    start_dates = soup.select(".eventInfoStartDate")
    start_times = soup.select(".eventInfoStartTime")

    if not (len(links) == len(start_dates) == len(start_times)) or not links:
        return []

    events: list[dict[str, Any]] = []
    for link, date_el, time_el in zip(links, start_dates, start_times):
        title = link.get_text(" ", strip=True)
        url = link.get("href") or source_url

        # The label preceding the date varies ("Start", "When", or no
        # label at all) - strip whatever the label element's own text
        # actually is, rather than assuming a fixed string.
        date_text = date_el.get_text(" ", strip=True)
        label_el = date_el.select_one(".eventInfoBoxLabel")
        label_text = label_el.get_text(" ", strip=True) if label_el else ""
        if label_text and date_text.startswith(label_text):
            date_text = date_text[len(label_text):].strip()

        time_text = time_el.get_text(" ", strip=True).strip()

        if not title or not date_text:
            continue
        try:
            start = dateparser.parse(f"{date_text} {time_text}".strip())
        except (ValueError, TypeError, OverflowError):
            continue

        events.append(
            {
                "title": title,
                "start": start,
                "end": None,
                "all_day": not time_text,
                "location": None,
                "description": None,
                "url": url,
            }
        )

    return events
