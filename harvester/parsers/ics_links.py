from __future__ import annotations

import base64
from datetime import datetime, time
from typing import Any

from bs4 import BeautifulSoup
from icalendar import Calendar


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)

# Some sites (e.g. Inland Empire Chamber, via the Spatie calendar-links
# PHP package) embed a full per-event ICS blob directly as a
# data:text/calendar;base64,... href on an "Add to calendar" link. That's
# already-structured data - decode and parse it with icalendar directly
# rather than scraping visible text.


def extract_ics_data_uri_events(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict[str, Any]] = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not href.startswith("data:text/calendar"):
            continue
        try:
            _, b64_data = href.split(",", 1)
            ics_bytes = base64.b64decode(b64_data)
            cal = Calendar.from_ical(ics_bytes)
        except Exception:  # noqa: BLE001 - skip malformed embeds
            continue

        for component in cal.walk("VEVENT"):
            summary = str(component.get("summary", "")).strip()
            dtstart = component.get("dtstart")
            if not summary or dtstart is None:
                continue

            description = component.get("description")
            location = component.get("location")
            dtend = component.get("dtend")
            all_day = not isinstance(dtstart.dt, datetime)

            events.append(
                {
                    "title": summary,
                    "start": _as_datetime(dtstart.dt),
                    "end": _as_datetime(dtend.dt) if dtend else None,
                    "all_day": all_day,
                    "location": str(location).strip() if location else None,
                    "description": str(description).strip() if description else None,
                    "url": source_url,
                }
            )

    return events
