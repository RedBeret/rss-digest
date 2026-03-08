"""SQLite-backed deduplication store for rss-digest."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .fetcher import Entry

_DEFAULT_DB = Path.home() / ".rss-digest" / "feeds.db"

_DDL = """
CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_url    TEXT    NOT NULL,
    guid        TEXT    NOT NULL,
    title       TEXT    NOT NULL DEFAULT '',
    summary     TEXT    NOT NULL DEFAULT '',
    link        TEXT    NOT NULL DEFAULT '',
    published   TEXT,
    seen_at     TEXT    NOT NULL,
    UNIQUE(feed_url, guid)
);

CREATE TABLE IF NOT EXISTS digests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    channel     TEXT    NOT NULL,
    sent_at     TEXT    NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DigestStore:
    """Persistent store for feed entries and digest history."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        with self._conn:
            self._conn.executescript(_DDL)

    def add_entries(self, entries: list[Entry]) -> list[Entry]:
        """Insert entries; return only the NEW ones (deduplication).

        Entries whose (feed_url, guid) pair already exists are silently skipped.
        """
        new_entries: list[Entry] = []
        seen_at = _now_iso()
        with self._conn:
            for entry in entries:
                published_str = entry.published.isoformat() if entry.published else None
                cursor = self._conn.execute(
                    """
                    INSERT OR IGNORE INTO entries
                        (feed_url, guid, title, summary, link, published, seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.feed_url,
                        entry.guid,
                        entry.title,
                        entry.summary,
                        entry.link,
                        published_str,
                        seen_at,
                    ),
                )
                if cursor.rowcount > 0:
                    new_entries.append(entry)
        return new_entries

    def has_digest_today(self, channel: str) -> bool:
        """Return True if a digest was already sent to *channel* today (UTC)."""
        today = datetime.now(timezone.utc).date().isoformat()
        row = self._conn.execute(
            "SELECT 1 FROM digests WHERE date = ? AND channel = ? LIMIT 1",
            (today, channel),
        ).fetchone()
        return row is not None

    def record_digest(self, channel: str) -> None:
        """Record that a digest was sent to *channel* now."""
        today = datetime.now(timezone.utc).date().isoformat()
        with self._conn:
            self._conn.execute(
                "INSERT INTO digests (date, channel, sent_at) VALUES (?, ?, ?)",
                (today, channel, _now_iso()),
            )

    def recent_digests(self, limit: int = 7) -> list[dict]:
        """Return the last *limit* digest records as dicts."""
        rows = self._conn.execute(
            "SELECT date, channel, sent_at FROM digests ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def entry_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        return row[0]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DigestStore":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
