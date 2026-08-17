from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    source: str
    title: str
    start: datetime
    end: datetime | None = None
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    url: str | None = None

    @property
    def uid(self) -> str:
        # Stable across runs so re-publishing the feed updates existing
        # calendar entries instead of duplicating them.
        basis = f"{self.source}|{self.title.strip().lower()}|{self.start.isoformat()}"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()
        return f"{digest}@chamber-events-harvester"
