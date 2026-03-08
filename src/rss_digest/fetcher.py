"""RSS/Atom feed fetching and entry parsing."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser


@dataclass
class Entry:
    """A single feed entry."""

    title: str
    summary: str
    link: str
    published: Optional[datetime]
    guid: str
    feed_name: str
    feed_url: str

    def __post_init__(self) -> None:
        # Sanitize: strip excessive whitespace
        self.title = self.title.strip()
        self.summary = self.summary.strip()


def _parse_published(entry: dict) -> Optional[datetime]:
    """Extract a timezone-aware datetime from a feedparser entry dict."""
    # feedparser provides published_parsed as a time.struct_time (UTC)
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        try:
            return datetime(
                t.tm_year, t.tm_mon, t.tm_mday,
                t.tm_hour, t.tm_min, t.tm_sec,
                tzinfo=timezone.utc,
            )
        except Exception:
            pass
    return None


def _entry_guid(entry: dict) -> str:
    """Return the best available unique identifier for a feed entry."""
    return (
        entry.get("id")
        or entry.get("link")
        or entry.get("title", "")
    )


def _entry_summary(entry: dict) -> str:
    """Extract the best available summary text."""
    # Try summary → content[0] → title fallback
    summary = entry.get("summary", "")
    if not summary and "content" in entry:
        content_list = entry["content"]
        if content_list:
            summary = content_list[0].get("value", "")
    return summary or ""


def fetch_feed(url: str, feed_name: str = "", timeout: int = 15) -> list[Entry]:
    """Fetch and parse a single RSS/Atom feed URL.

    Args:
        url: Feed URL.
        feed_name: Human-readable name shown in digests.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of Entry objects (newest first).

    Raises:
        ValueError: If the feed could not be fetched or parsed.
    """
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        parsed = feedparser.parse(url)
    finally:
        socket.setdefaulttimeout(old_timeout)

    # feedparser doesn't raise on network errors — check bozo_exception
    if parsed.get("bozo") and not parsed.get("entries"):
        exc = parsed.get("bozo_exception")
        raise ValueError(f"Failed to parse feed {url!r}: {exc}")

    display_name = feed_name or parsed.feed.get("title", url)

    entries: list[Entry] = []
    for raw in parsed.entries:
        entries.append(
            Entry(
                title=raw.get("title", "(no title)"),
                summary=_entry_summary(raw),
                link=raw.get("link", ""),
                published=_parse_published(raw),
                guid=_entry_guid(raw),
                feed_name=display_name,
                feed_url=url,
            )
        )

    return entries


def fetch_feeds(feed_configs: list[dict]) -> list[Entry]:
    """Fetch multiple feeds from a list of ``{"url": ..., "name": ...}`` dicts.

    Errors on individual feeds are printed but do not abort the run.

    Returns:
        Combined list of entries from all feeds (order preserved per feed).
    """
    all_entries: list[Entry] = []
    for cfg in feed_configs:
        url = cfg.get("url", "")
        name = cfg.get("name", "")
        if not url:
            continue
        try:
            entries = fetch_feed(url, feed_name=name)
            all_entries.extend(entries)
        except Exception as exc:
            print(f"[warn] Failed to fetch {url!r}: {exc}")
    return all_entries
