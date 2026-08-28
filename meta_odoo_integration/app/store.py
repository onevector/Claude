import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ProcessedLeadsStore:
    """Local record of which Meta leadgen_ids have already been pushed to
    Odoo. Meta redelivers webhooks it doesn't get a fast 200 for, and can
    also occasionally send the same leadgen event more than once - this
    stops those from becoming duplicate Odoo leads."""

    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS processed_leads (
                leadgen_id TEXT PRIMARY KEY,
                odoo_lead_id INTEGER NOT NULL,
                processed_at TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def is_processed(self, leadgen_id: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM processed_leads WHERE leadgen_id = ?", (leadgen_id,))
        return cur.fetchone() is not None

    def mark_processed(self, leadgen_id: str, odoo_lead_id: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO processed_leads (leadgen_id, odoo_lead_id, processed_at) VALUES (?, ?, ?)",
            (leadgen_id, odoo_lead_id, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()


class DeadLetterQueue:
    """Append-only JSONL log of leads that failed to process, so nothing
    is silently dropped when Meta's API or Odoo is briefly unavailable.
    Reprocess with scripts/reprocess_failed.py."""

    def __init__(self, path: Path):
        self._path = path

    def add(self, leadgen_id: str, error: str) -> None:
        entry = {
            "leadgen_id": leadgen_id,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open() as f:
            return [json.loads(line) for line in f if line.strip()]

    def clear(self) -> None:
        self._path.write_text("")

    def rewrite(self, entries: list[dict]) -> None:
        with self._path.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
