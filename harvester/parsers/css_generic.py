from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser


def extract_css_events(html: str, source_url: str, css: dict[str, str]) -> list[dict[str, Any]]:
    """Fallback scraper for sites without schema.org JSON-LD Event markup.

    `css` is a per-site selector config (see config/sites.yaml), e.g.:
      item: ".event-list .event-item"
      title: ".event-title"
      start: ".event-date"
      location: ".event-location"      # optional
      description: ".event-description"  # optional
      link: "a"                          # optional, resolved to absolute URL
    """
    soup = BeautifulSoup(html, "html.parser")
    item_selector = css.get("item")
    if not item_selector:
        return []

    events: list[dict[str, Any]] = []
    for item in soup.select(item_selector):
        title_el = item.select_one(css["title"]) if css.get("title") else None
        start_el = item.select_one(css["start"]) if css.get("start") else None
        if title_el is None or start_el is None:
            continue

        title = title_el.get_text(" ", strip=True)
        start_text = start_el.get_text(" ", strip=True)
        if not title or not start_text:
            continue

        try:
            start = dateparser.parse(start_text, fuzzy=True)
        except (ValueError, TypeError, OverflowError):
            continue

        location = None
        if css.get("location"):
            loc_el = item.select_one(css["location"])
            if loc_el is not None:
                location = loc_el.get_text(" ", strip=True) or None

        description = None
        if css.get("description"):
            desc_el = item.select_one(css["description"])
            if desc_el is not None:
                description = desc_el.get_text(" ", strip=True) or None

        url = source_url
        if css.get("link"):
            link_el = item.select_one(css["link"])
            if link_el is not None and link_el.get("href"):
                url = urljoin(source_url, link_el["href"])

        events.append(
            {
                "title": title,
                "start": start,
                "end": None,
                "all_day": ":" not in start_text,
                "location": location,
                "description": description,
                "url": url,
            }
        )

    return events
