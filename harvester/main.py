from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

from .fetchers import fetch_html
from .ics_writer import write_ics
from .models import Event
from .parsers.css_generic import extract_css_events
from .parsers.jsonld import extract_json_ld_events

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("harvester")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
OUTPUT_PATH = ROOT / "docs" / "events.ics"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def diagnose(html: str) -> str:
    """Best-effort diagnostics logged when a site yields zero events, so
    selector/parser fixes can be made from CI logs alone."""
    lowered = html.lower()
    has_ld_json = "application/ld+json" in lowered
    mentions_event_type = '"@type": "event"' in lowered or '"@type":"event"' in lowered
    title_start = lowered.find("<title>")
    title_snippet = html[title_start : title_start + 150] if title_start != -1 else "(no <title> found)"
    return (
        f"html_length={len(html)} has_ld_json_script={has_ld_json} "
        f"mentions_event_type={mentions_event_type} title_snippet={title_snippet!r}"
    )


def harvest_site(site: dict) -> list[Event]:
    name = site["name"]
    url = site["url"]
    parser = site.get("parser", "jsonld")

    log.info("Fetching %s (%s)", name, url)
    try:
        html = fetch_html(url)
    except Exception as exc:  # noqa: BLE001 - keep other sites running
        log.error("Failed to fetch %s: %s", name, exc)
        return []

    raw_events: list[dict] = []

    if parser in ("jsonld", "jsonld+css"):
        raw_events = extract_json_ld_events(html, url)

    if not raw_events and parser in ("css", "jsonld+css"):
        css = site.get("css") or {}
        raw_events = extract_css_events(html, url, css)

    if not raw_events:
        log.warning("No events found for %s. Diagnostics: %s", name, diagnose(html))
        return []

    events = [Event(source=name, **raw) for raw in raw_events]
    log.info("Found %d event(s) for %s", len(events), name)
    return events


def main() -> None:
    config = load_config(CONFIG_PATH)
    all_events: list[Event] = []
    empty_sites: list[str] = []

    for site in config["sites"]:
        events = harvest_site(site)
        if not events:
            empty_sites.append(site["name"])
        all_events.extend(events)

    write_ics(
        all_events,
        OUTPUT_PATH,
        calendar_name=config.get("calendar_name", "Chamber Events"),
        timezone_name=config.get("timezone", "America/Los_Angeles"),
    )
    log.info("Wrote %d total event(s) to %s", len(all_events), OUTPUT_PATH)

    if empty_sites:
        log.warning(
            "%d site(s) returned zero events (may need a `css` selector block "
            "in config/sites.yaml): %s",
            len(empty_sites),
            ", ".join(empty_sites),
        )

    if not all_events and config["sites"]:
        log.error("No events harvested from any site - failing the run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
