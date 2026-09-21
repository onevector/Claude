"""One-off diagnostic: find where organizer/contact info lives for the
currently-working sites, and check the surrounding HTML around Inland
Empire Chamber's embedded ICS link for a real per-event URL.

- ChamberMaster (Glendora): fetch one event detail page, look for any
  class mentioning organizer/contact/host/sponsor near the already-known
  .gz-event-date / .gz-event-location fields.
- ABAIE: fetch one event detail page (the summary widget has no location
  or organizer at all) and look for the same.
- Inland Empire Chamber: the embedded ICS blob itself has no ORGANIZER or
  URL field (confirmed by decoding it directly) - check the anchor/element
  surrounding the "calender ICS" link for a real event-page link and any
  organizer/host name nearby.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

ORG_HINTS = re.compile(r"organiz|contact|host|sponsor|presented|speaker", re.I)


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH ERROR {url}: {exc}")
        return None
    return BeautifulSoup(resp.text, "html.parser")


def scan_for_organizer_hints(soup: BeautifulSoup, label: str) -> None:
    seen: set[str] = set()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if cls in seen:
                continue
            if ORG_HINTS.search(cls):
                seen.add(cls)
                text = tag.get_text(" ", strip=True)[:200]
                print(f"[{label}] class={cls!r} text={text!r}")
    if not seen:
        print(f"[{label}] no organizer/contact/host-ish class names found.")


def chambermaster_detail() -> None:
    section("Glendora ChamberMaster: event detail page - organizer scan")
    list_soup = fetch("https://business.glendora-chamber.org/events/calendarcatgid/6")
    if list_soup is None:
        return
    link = list_soup.select_one(".gz-cal-event a[href]")
    if link is None:
        print("No event link found on list page.")
        return
    detail_url = link["href"].split("?")[0]
    print(f"detail_url={detail_url}")
    detail_soup = fetch(detail_url)
    if detail_soup is None:
        return
    scan_for_organizer_hints(detail_soup, "glendora-detail")

    # Also dump the full main content area text so we can eyeball anything
    # the class-name heuristic misses (e.g. plain text "Contact: Jane Doe").
    main = detail_soup.select_one(".gz-event-detail") or detail_soup.find("main") or detail_soup.body
    if main:
        print("\nFull detail-page text (first 2500 chars):")
        print(main.get_text(" | ", strip=True)[:2500])


def abaie_detail() -> None:
    section("ABAIE: event detail page - location + organizer scan")
    list_soup = fetch("https://abaie.org/events")
    if list_soup is None:
        return
    link = list_soup.select_one(".eventDetailsLink")
    if link is None:
        print("No .eventDetailsLink found.")
        return
    detail_url = link["href"]
    print(f"detail_url={detail_url}")
    detail_soup = fetch(detail_url)
    if detail_soup is None:
        return
    scan_for_organizer_hints(detail_soup, "abaie-detail")

    # Look specifically for location-ish classes too, since the summary
    # widget never has it.
    loc_hints = re.compile(r"location|venue|address|where", re.I)
    seen = set()
    for tag in detail_soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if cls in seen or not loc_hints.search(cls):
                continue
            seen.add(cls)
            print(f"[abaie-detail] LOCATION class={cls!r} text={tag.get_text(' ', strip=True)[:200]!r}")
    if not seen:
        print("[abaie-detail] no location-ish class names found.")

    main = detail_soup.find("main") or detail_soup.body
    if main:
        print("\nFull detail-page text (first 3000 chars):")
        print(main.get_text(" | ", strip=True)[:3000])


def iechamber_context() -> None:
    section("Inland Empire Chamber: context around embedded ICS link")
    soup = fetch("https://www.iechamber.org/events")
    if soup is None:
        return
    ics_link = None
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("data:text/calendar"):
            ics_link = a
            break
    if ics_link is None:
        print("No data:text/calendar link found.")
        return

    # Walk up a few ancestors looking for a normal <a href> pointing at a
    # real event page, and any text that looks like an organizer/host name.
    node = ics_link
    for depth in range(6):
        node = node.parent
        if node is None or not getattr(node, "get", None):
            break
        classes = node.get("class")
        print(f"ancestor depth={depth} tag={node.name} class={classes}")
        for a in node.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("data:") and href not in ("#", ""):
                print(f"    real link: {href!r} text={a.get_text(strip=True)!r}")

    # Print the whole ancestor block's text at a reasonable depth up so we
    # can see title/organizer/date text around the ICS link by eye.
    node = ics_link
    for _ in range(4):
        if node.parent is None:
            break
        node = node.parent
    print("\nBlock text:")
    print(node.get_text(" | ", strip=True)[:2000])


def main() -> None:
    for fn in (chambermaster_detail, abaie_detail, iechamber_context):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f"\n{fn.__name__} FAILED: {exc}")


if __name__ == "__main__":
    main()
