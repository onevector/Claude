from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

from .fetchers import fetch_html, fetch_rendered_html
from .ics_writer import write_ics
from .models import Event
from .parsers.abaie import extract_abaie_events
from .parsers.chambermaster import extract_chambermaster_events
from .parsers.css_generic import extract_css_events
from .parsers.ics_links import extract_ics_data_uri_events
from .parsers.jsonld import extract_json_ld_events

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("harvester")

# Each parser takes (html, source_url) and returns a list of raw event
# dicts (see models.Event fields). `jsonld` is tried first for every site
# unless overridden, since it needs no per-site tuning; the rest are
# site-specific strategies discovered by inspecting each platform's markup.
PARSERS = {
    "jsonld": extract_json_ld_events,
    "chambermaster": extract_chambermaster_events,
    "abaie": extract_abaie_events,
    "ics_links": extract_ics_data_uri_events,
}

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

    render = bool(site.get("render"))
    log.info("Fetching %s (%s)%s", name, url, " [rendered]" if render else "")
    try:
        html = fetch_rendered_html(url) if render else fetch_html(url)
    except Exception as exc:  # noqa: BLE001 - keep other sites running
        log.error("Failed to fetch %s: %s", name, exc)
        return []

    raw_events: list[dict] = []

    if parser == "css":
        raw_events = extract_css_events(html, url, site.get("css") or {})
    elif parser in PARSERS:
        raw_events = PARSERS[parser](html, url)
        # Optional per-site CSS fallback if the primary parser strategy
        # comes up empty (e.g. a platform migration breaks it).
        if not raw_events and site.get("css"):
            raw_events = extract_css_events(html, url, site["css"])
    else:
        log.error("Unknown parser %r for %s; skipping.", parser, name)
        return []

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
