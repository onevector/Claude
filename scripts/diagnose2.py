"""Second-pass diagnostics, targeted at specific open questions from the
first diagnose.py run:

- Glendora (GrowthZone/ChamberMaster): what does an event *detail* page
  look like? The calendar grid only has title + link, no date/time/location.
- ABAIE: what's the actual repeating *event row* container (parent of
  .eventDetailsLink), not just the individual label/value spans?
- ABALA: why did the heuristic find nothing in a 1.18MB page? Look for
  SPA data blobs / iframes.
- Inland Empire Chamber: how many data:text/calendar links are on the
  page, and what do they decode to?
- Irwindale: does a standard browser User-Agent get past the 403?
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def glendora_detail_page() -> None:
    section("Glendora: sample event detail page")
    list_url = "https://business.glendora-chamber.org/events/calendarcatgid/6"
    resp = requests.get(list_url, headers=DEFAULT_HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.select_one(".gz-cal-event a[href]")
    if not link:
        print("No event link found on list page.")
        return
    detail_url = link["href"]
    print(f"detail_url={detail_url}")
    detail_resp = requests.get(detail_url, headers=DEFAULT_HEADERS, timeout=20)
    print(f"status={detail_resp.status_code} length={len(detail_resp.text)}")
    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

    interesting = re.compile(r"date|time|location|address|when|where", re.I)
    seen = set()
    for tag in detail_soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if interesting.search(cls) and cls not in seen:
                seen.add(cls)
                text = tag.get_text(" ", strip=True)[:150]
                print(f"  class={cls!r} text={text!r}")

    if not seen:
        print("No date/time/location-ish classes found. Dumping main content text:")
        main = detail_soup.find("main") or detail_soup.body
        if main:
            print(main.get_text(" ", strip=True)[:2000])


def abaie_event_row() -> None:
    section("ABAIE: ancestor chain of .eventDetailsLink")
    resp = requests.get("https://abaie.org/events", headers=DEFAULT_HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")
    link = soup.select_one(".eventDetailsLink")
    if not link:
        print("No .eventDetailsLink found.")
        return
    node = link
    for depth in range(5):
        node = node.parent
        if node is None or not getattr(node, "get", None):
            break
        classes = node.get("class")
        node_id = node.get("id")
        print(f"depth={depth} tag={node.name} class={classes} id={node_id}")
    # Print the row a couple levels up, which likely wraps title+date+time.
    ancestor = link
    for _ in range(3):
        if ancestor.parent is None:
            break
        ancestor = ancestor.parent
    print("\nRow HTML snippet:")
    print(ancestor.prettify()[:2500])


def abala_investigation() -> None:
    section("ABALA: why no matches in 1.18MB page")
    resp = requests.get("https://www.abala.org/aba-events", headers=DEFAULT_HEADERS, timeout=20)
    text = resp.text
    print(f"status={resp.status_code} length={len(text)}")
    soup = BeautifulSoup(text, "html.parser")

    scripts_with_ids = [s.get("id") for s in soup.find_all("script") if s.get("id")]
    print(f"script ids (first 20): {scripts_with_ids[:20]}")

    for marker in ("__NEXT_DATA__", "__INITIAL_STATE__", "window.__", "wixBiSession", "Squarespace", "webflow", "shopify"):
        if marker.lower() in text.lower():
            print(f"marker found: {marker!r}")

    iframes = [f.get("src") for f in soup.find_all("iframe") if f.get("src")]
    print(f"iframes (first 10): {iframes[:10]}")

    # generic word 'event' occurrences as class substrings, without the
    # min-count filter, to see if there's anything at all
    any_event_classes = set()
    for tag in soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if "event" in cls.lower():
                any_event_classes.add(cls)
    print(f"any class containing 'event' (uncounted): {sorted(any_event_classes)[:30]}")


def iechamber_ics_links() -> None:
    section("Inland Empire Chamber: all data:text/calendar links")
    resp = requests.get("https://www.iechamber.org/events", headers=DEFAULT_HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")
    links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("data:text/calendar")]
    print(f"count={len(links)}")
    for href in links[:10]:
        b64 = href.split(",", 1)[1]
        decoded = base64.b64decode(b64).decode("utf-8", errors="replace")
        print("---")
        print(decoded)


def irwindale_user_agent_test() -> None:
    section("Irwindale: retry with standard browser User-Agent")
    url = "https://www.irwindalechamber.org/test-calendar"
    for label, headers in (("bot-ua", DEFAULT_HEADERS), ("browser-ua", BROWSER_HEADERS)):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            print(f"{label}: status={resp.status_code} length={len(resp.text)}")
            if resp.status_code != 200:
                print(f"  body snippet: {resp.text[:300]!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"{label}: ERROR {exc}")

    # Also check the site's homepage / a likely real events page in case
    # /test-calendar is a stale placeholder slug.
    for candidate in ("https://www.irwindalechamber.org/", "https://www.irwindalechamber.org/events", "https://www.irwindalechamber.org/calendar"):
        try:
            resp = requests.get(candidate, headers=BROWSER_HEADERS, timeout=20)
            print(f"candidate {candidate}: status={resp.status_code} length={len(resp.text)}")
        except Exception as exc:  # noqa: BLE001
            print(f"candidate {candidate}: ERROR {exc}")


def main() -> None:
    glendora_detail_page()
    abaie_event_row()
    abala_investigation()
    iechamber_ics_links()
    irwindale_user_agent_test()


if __name__ == "__main__":
    main()
