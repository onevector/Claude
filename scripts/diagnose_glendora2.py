"""Check Glendora's new /events page structure (their calendarcatgid URL
404s now) - does it still use .gz-cal-event, or a new template?
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harvester.fetchers import DEFAULT_HEADERS  # noqa: E402

resp = requests.get("https://business.glendora-chamber.org/events", headers=DEFAULT_HEADERS, timeout=20)
print(f"status={resp.status_code} length={len(resp.text)}")
soup = BeautifulSoup(resp.text, "html.parser")

for cls in ("gz-cal-event", "gz-event-date", "gz-event-location"):
    els = soup.find_all(class_=cls)
    print(f"class={cls!r} count={len(els)}")

# find repeating event-ish containers around the /events/Details/ links
detail_links = [a for a in soup.find_all("a", href=True) if "/events/Details/" in a["href"]]
print(f"\n/events/Details/ links found: {len(detail_links)}")
if detail_links:
    link = detail_links[0]
    print(f"first link href={link['href']!r} text={link.get_text(' ', strip=True)!r} class={link.get('class')}")
    # walk up ancestors to find the repeating card/row container
    node = link
    for depth in range(6):
        node = node.parent
        if node is None or not getattr(node, "get", None):
            break
        print(f"ancestor depth={depth} tag={node.name} class={node.get('class')}")

    # dump the likely card container
    node = link
    for _ in range(3):
        if node.parent is None:
            break
        node = node.parent
    print("\nCard HTML snippet:")
    print(node.prettify()[:2500])

    # fetch the detail page itself to see the new date/location/organizer markup
    detail_resp = requests.get(link["href"], headers=DEFAULT_HEADERS, timeout=20)
    print(f"\ndetail status={detail_resp.status_code} length={len(detail_resp.text)}")
    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
    import re
    hint_re = re.compile(r"date|time|location|venue|organiz|contact|host", re.I)
    seen = set()
    for tag in detail_soup.find_all(class_=True):
        for cls in tag.get("class", []):
            if cls in seen or not hint_re.search(cls):
                continue
            seen.add(cls)
            print(f"[detail] class={cls!r} text={tag.get_text(' ', strip=True)[:200]!r}")
