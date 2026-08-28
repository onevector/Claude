"""Retry every lead currently sitting in the dead-letter queue.

Run this after fixing whatever caused failures (expired token, Odoo
downtime, a bad field mapping). Successfully reprocessed entries are
removed from the queue; entries that fail again are kept for next time.

Usage: python -m scripts.reprocess_failed
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_settings  # noqa: E402
from app.pipeline import Pipeline  # noqa: E402


async def main() -> None:
    settings = load_settings()
    pipeline = Pipeline(settings)

    entries = pipeline.dead_letter.read_all()
    if not entries:
        print("Dead-letter queue is empty.")
        return

    print(f"Retrying {len(entries)} failed lead(s)...")
    # Clear the file first - process_leadgen_id() re-appends a fresh entry
    # for anything that fails again, so the file ends up holding only
    # this run's failures.
    pipeline.dead_letter.clear()
    unique_ids = list(dict.fromkeys(e["leadgen_id"] for e in entries))
    for leadgen_id in unique_ids:
        await pipeline.process_leadgen_id(leadgen_id)

    remaining = pipeline.dead_letter.read_all()
    succeeded = len(unique_ids) - len(remaining)
    print(f"Done. {succeeded} succeeded, {len(remaining)} still failing.")


if __name__ == "__main__":
    asyncio.run(main())
