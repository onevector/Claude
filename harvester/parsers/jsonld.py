from __future__ import annotations

import json
from typing import Any, Iterator

from bs4 import BeautifulSoup
from dateutil import parser as dateparser


def extract_json_ld_events(html: str, source_url: str) -> list[dict[str, Any]]:
    """Find schema.org Event nodes in <script type="application/ld+json"> blocks."""
    soup = BeautifulSoup(html, "html.parser")
    events: list[dict[str, Any]] = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for node in _walk_nodes(data):
            if not _is_event(node):
                continue
            parsed = _node_to_event(node, source_url)
            if parsed is not None:
                events.append(parsed)

    return events


def _walk_nodes(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            yield from _walk_nodes(item)
    elif isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            for item in data["@graph"]:
                yield from _walk_nodes(item)
        else:
            yield data


def _is_event(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return any(str(t).lower() == "event" for t in node_type)
    return isinstance(node_type, str) and node_type.lower() == "event"


def _node_to_event(node: dict[str, Any], source_url: str) -> dict[str, Any] | None:
    name = node.get("name")
    start_raw = node.get("startDate")
    if not isinstance(name, str) or not name.strip() or not start_raw:
        return None

    try:
        start = dateparser.parse(str(start_raw))
    except (ValueError, TypeError, OverflowError):
        return None

    end = None
    end_raw = node.get("endDate")
    if end_raw:
        try:
            end = dateparser.parse(str(end_raw))
        except (ValueError, TypeError, OverflowError):
            end = None

    description = node.get("description")
    if isinstance(description, str):
        description = BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
    else:
        description = None

    url = node.get("url") or source_url
    if not isinstance(url, str):
        url = source_url

    all_day = "T" not in str(start_raw)

    return {
        "title": name.strip(),
        "start": start,
        "end": end,
        "all_day": all_day,
        "location": _location_to_str(node.get("location")),
        "description": description,
        "url": url,
    }


def _location_to_str(location: Any) -> str | None:
    if location is None:
        return None
    if isinstance(location, list):
        location = location[0] if location else None
    if isinstance(location, str):
        return location
    if isinstance(location, dict):
        parts: list[str] = []
        name = location.get("name")
        if isinstance(name, str) and name.strip():
            parts.append(name.strip())

        address = location.get("address")
        if isinstance(address, dict):
            addr_parts = [
                address.get("streetAddress"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("postalCode"),
            ]
            addr_str = ", ".join(p for p in addr_parts if isinstance(p, str) and p.strip())
            if addr_str:
                parts.append(addr_str)
        elif isinstance(address, str) and address.strip():
            parts.append(address.strip())

        return " - ".join(parts) if parts else None
    return None
