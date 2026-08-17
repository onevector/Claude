from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar
from icalendar import Event as ICalEvent
from icalendar import vText

from .models import Event


def _normalize_tz(value: datetime, tz: ZoneInfo) -> datetime:
    """Convert to the feed's IANA zone so icalendar emits a proper TZID
    instead of silently dropping a fixed UTC-offset (e.g. from dateutil)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def write_ics(
    events: list[Event],
    out_path: Path,
    calendar_name: str,
    timezone_name: str,
) -> None:
    tz = ZoneInfo(timezone_name)
    cal = Calendar()
    cal.add("prodid", "-//Chamber Events Harvester//onevector//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-timezone", timezone_name)
    # Hint most subscribers (Apple/Outlook; Google mostly sets its own cadence)
    # honor to poll roughly twice a day.
    cal.add("x-published-ttl", "PT12H")

    def sort_key(event: Event) -> datetime:
        return _normalize_tz(event.start, tz)

    dtstamp = datetime.now(timezone.utc)
    for event in sorted(events, key=sort_key):
        ve = ICalEvent()
        ve.add("uid", event.uid)
        ve.add("summary", event.title)
        ve.add("dtstamp", dtstamp)

        start = _normalize_tz(event.start, tz)

        if event.all_day:
            start_date = start.date()
            end_date = _normalize_tz(event.end, tz).date() if event.end else start_date
            if end_date <= start_date:
                end_date = start_date + timedelta(days=1)
            ve.add("dtstart", start_date)
            ve.add("dtend", end_date)
        else:
            end = _normalize_tz(event.end, tz) if event.end else start + timedelta(hours=1)
            ve.add("dtstart", start)
            ve.add("dtend", end)

        if event.location:
            ve.add("location", vText(event.location))
        if event.description:
            ve.add("description", vText(event.description))
        if event.url:
            ve.add("url", event.url)
        ve.add("categories", [event.source])

        cal.add_component(ve)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(cal.to_ical())
