"""Fifth-pass diagnostics, closing the three remaining gaps from diagnose4:
- Irwindale: found FullCalendar.js (.fc-daygrid-day-events) but need the
  actual event chip classes (.fc-event, .fc-event-title, etc).
- ABALA: still zero content after JS rendering - check for iframes
  (possibly injected after initial render) and any Wix-events-specific
  script/network hints.
- Glue Up: the root iercc.glueup.com page is a landing page, not an
  events list - look for the real events URL and check it directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import fetch_rendered_html  # noqa: E402


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def irwindale_fullcalendar() -> None:
    section("Irwindale: FullCalendar event chips")
    html = fetch_rendered_html("https://www.irwindalechamber.org/test-calendar", wait_ms=4000)
    soup = BeautifulSoup(html, "html.parser")

    for cls in ("fc-event", "fc-daygrid-event", "fc-event-title", "fc-h-event", "fc-list-event"):
        elements = soup.find_all(class_=cls)
        print(f"class={cls!r} count={len(elements)}")
        if elements:
            print(elements[0].prettify()[:1500])

    # dump a non-empty day cell if any exist
    for day in soup.select(".fc-daygrid-day"):
        events_container = day.select_one(".fc-daygrid-day-events")
        if events_container and events_container.find(True):
            print("\nFirst day cell WITH content:")
            print(day.prettify()[:2000])
            break
    else:
        print("\nNo day cell has any child content in .fc-daygrid-day-events.")


def abala_iframe_recheck() -> None:
    section("ABALA: iframe/network recheck after render")
    html = fetch_rendered_html("https://www.abala.org/aba-events", wait_ms=5000)
    soup = BeautifulSoup(html, "html.parser")

    iframes = soup.find_all("iframe")
    print(f"iframe count: {len(iframes)}")
    for f in iframes:
        print(f"  src={f.get('src')!r} id={f.get('id')!r}")

    for marker in ("wix-events", "wixevents", "events-widget", "eventswidget"):
        if marker in html.lower():
            print(f"marker found in HTML: {marker!r}")


def glueup_find_events_url() -> None:
    section("Glue Up: find the real events listing URL")
    html = fetch_rendered_html("https://iercc.glueup.com/", wait_ms=3000)
    soup = BeautifulSoup(html, "html.parser")

    candidates = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "event" in href.lower():
            candidates.add(href)
    print("links containing 'event':")
    for href in sorted(candidates)[:20]:
        print(f"  {href}")

    # Try the conventional /events path directly too.
    for path in ("events", "events/list", "events/upcoming"):
        url = f"https://iercc.glueup.com/{path}"
        try:
            events_html = fetch_rendered_html(url, wait_ms=3000)
        except Exception as exc:  # noqa: BLE001
            print(f"{url}: ERROR {exc}")
            continue
        print(f"{url}: rendered length={len(events_html)}")


def main() -> None:
    irwindale_fullcalendar()
    abala_iframe_recheck()
    glueup_find_events_url()


if __name__ == "__main__":
    main()
