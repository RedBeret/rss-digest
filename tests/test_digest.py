"""Tests for rss_digest.digest (formatting)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rss_digest.digest import format_digest, _truncate_summary
from rss_digest.fetcher import Entry


def _entry(title: str, summary: str = "", link: str = "http://example.com", feed: str = "Feed") -> Entry:
    return Entry(
        title=title,
        summary=summary,
        link=link,
        published=datetime(2026, 3, 8, tzinfo=timezone.utc),
        guid=title,
        feed_name=feed,
        feed_url="http://feed.example/rss",
    )


# ---------------------------------------------------------------------------
# _truncate_summary
# ---------------------------------------------------------------------------

def test_truncate_summary_strips_html():
    text = "<p>Hello <b>world</b></p>"
    result = _truncate_summary(text, max_chars=100)
    assert "<" not in result
    assert "Hello" in result
    assert "world" in result


def test_truncate_summary_truncates_long_text():
    text = "A" * 300
    result = _truncate_summary(text, max_chars=50)
    assert len(result) <= 50
    assert result.endswith("…")


def test_truncate_summary_returns_short_text_unchanged():
    text = "Short summary"
    result = _truncate_summary(text, max_chars=200)
    assert result == "Short summary"


# ---------------------------------------------------------------------------
# format_digest
# ---------------------------------------------------------------------------

def test_format_digest_empty_entries():
    result = format_digest([])
    assert "No new entries" in result


def test_format_digest_includes_feed_names():
    entries = [_entry("Story A", feed="Hacker News"), _entry("Story B", feed="Ars Technica")]
    result = format_digest(entries)
    assert "Hacker News" in result
    assert "Ars Technica" in result


def test_format_digest_includes_titles():
    entries = [_entry("Important News Story", summary="Details here.")]
    result = format_digest(entries)
    assert "Important News Story" in result


def test_format_digest_includes_links():
    entries = [_entry("Title", link="http://specific-link.example")]
    result = format_digest(entries)
    assert "http://specific-link.example" in result


def test_format_digest_respects_max_chars():
    # Generate many entries to exceed the default limit
    entries = [_entry(f"Story {i}", summary="x" * 500) for i in range(50)]
    result = format_digest(entries, max_chars=500)
    assert len(result) <= 504  # small tolerance for ellipsis


def test_format_digest_groups_by_feed():
    entries = [
        _entry("A1", feed="Feed A"),
        _entry("A2", feed="Feed A"),
        _entry("B1", feed="Feed B"),
    ]
    result = format_digest(entries)
    # Both Feed A section and Feed B section should be present
    assert "Feed A" in result
    assert "Feed B" in result
    # A1 and A2 should appear near each other (before B1's section)
    idx_a1 = result.index("A1")
    idx_a2 = result.index("A2")
    idx_b_section = result.index("Feed B")
    assert idx_a1 < idx_b_section
    assert idx_a2 < idx_b_section


def test_format_digest_includes_date_header():
    result = format_digest([_entry("X")])
    assert "RSS Digest" in result


def test_format_digest_no_summary_still_renders():
    entries = [_entry("Title Only", summary="")]
    result = format_digest(entries)
    assert "Title Only" in result


def test_format_digest_html_summary_is_stripped():
    entries = [_entry("T", summary="<p>Hello <b>World</b></p>")]
    result = format_digest(entries)
    assert "<p>" not in result
    assert "Hello" in result
