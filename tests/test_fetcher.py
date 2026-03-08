"""Tests for rss_digest.fetcher."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from rss_digest.fetcher import Entry, _entry_guid, _entry_summary, _parse_published, fetch_feed, fetch_feeds


# ---------------------------------------------------------------------------
# _parse_published
# ---------------------------------------------------------------------------

def _make_struct(year=2026, month=3, day=8, hour=12, minute=0, second=0):
    return time.struct_time((year, month, day, hour, minute, second, 0, 67, 0))


def test_parse_published_from_published_parsed():
    entry = {"published_parsed": _make_struct(2026, 3, 8, 10, 30, 0)}
    dt = _parse_published(entry)
    assert dt == datetime(2026, 3, 8, 10, 30, 0, tzinfo=timezone.utc)


def test_parse_published_falls_back_to_updated_parsed():
    entry = {"updated_parsed": _make_struct(2026, 1, 15, 6, 0, 0)}
    dt = _parse_published(entry)
    assert dt == datetime(2026, 1, 15, 6, 0, 0, tzinfo=timezone.utc)


def test_parse_published_missing_returns_none():
    assert _parse_published({}) is None


# ---------------------------------------------------------------------------
# _entry_guid
# ---------------------------------------------------------------------------

def test_entry_guid_prefers_id():
    assert _entry_guid({"id": "abc", "link": "http://x"}) == "abc"


def test_entry_guid_falls_back_to_link():
    assert _entry_guid({"link": "http://x"}) == "http://x"


def test_entry_guid_falls_back_to_title():
    assert _entry_guid({"title": "My Title"}) == "My Title"


def test_entry_guid_empty_dict():
    assert _entry_guid({}) == ""


# ---------------------------------------------------------------------------
# _entry_summary
# ---------------------------------------------------------------------------

def test_entry_summary_returns_summary_field():
    assert _entry_summary({"summary": "Hello"}) == "Hello"


def test_entry_summary_falls_back_to_content():
    entry = {"content": [{"value": "Content text"}]}
    assert _entry_summary(entry) == "Content text"


def test_entry_summary_returns_empty_when_none():
    assert _entry_summary({}) == ""


# ---------------------------------------------------------------------------
# fetch_feed
# ---------------------------------------------------------------------------

def _mock_parsed(entries_raw, bozo=False, feed_title="Test Feed"):
    parsed = MagicMock()
    parsed.get = lambda k, default=None: {
        "bozo": bozo,
        "bozo_exception": Exception("bad") if bozo else None,
        "entries": entries_raw,
    }.get(k, default)
    parsed.entries = entries_raw
    parsed.feed = MagicMock()
    parsed.feed.get = lambda k, default=None: feed_title if k == "title" else default
    return parsed


def _raw_entry(title="Story 1", link="http://example.com/1", guid="guid-1", summary="Summary text"):
    e = MagicMock()
    e.get = lambda k, default=None: {
        "title": title,
        "link": link,
        "id": guid,
        "summary": summary,
    }.get(k, default)
    e.__contains__ = lambda self, k: k in {"title", "link", "id", "summary"}
    e.get.__func__ = lambda s, k, d=None: {"title": title, "link": link, "id": guid, "summary": summary}.get(k, d)
    # Make it behave like a dict for feedparser patterns
    return {
        "title": title,
        "link": link,
        "id": guid,
        "summary": summary,
    }


@patch("rss_digest.fetcher.feedparser.parse")
def test_fetch_feed_returns_entries(mock_parse):
    raw = _raw_entry()
    mock_parse.return_value = _mock_parsed([raw])
    entries = fetch_feed("http://feed.example/rss", feed_name="Example")
    assert len(entries) == 1
    assert entries[0].title == "Story 1"
    assert entries[0].feed_name == "Example"
    assert entries[0].link == "http://example.com/1"


@patch("rss_digest.fetcher.feedparser.parse")
def test_fetch_feed_raises_on_bozo_with_no_entries(mock_parse):
    mock_parse.return_value = _mock_parsed([], bozo=True)
    with pytest.raises(ValueError, match="Failed to parse feed"):
        fetch_feed("http://bad.example/rss")


@patch("rss_digest.fetcher.feedparser.parse")
def test_fetch_feed_uses_feed_title_as_name_when_not_specified(mock_parse):
    raw = _raw_entry()
    mock_parse.return_value = _mock_parsed([raw], feed_title="Ars Technica")
    entries = fetch_feed("http://feed.example/rss")
    assert entries[0].feed_name == "Ars Technica"


@patch("rss_digest.fetcher.feedparser.parse")
def test_fetch_feed_empty_entries(mock_parse):
    mock_parse.return_value = _mock_parsed([])
    assert fetch_feed("http://empty.example/rss") == []


# ---------------------------------------------------------------------------
# fetch_feeds (multi-feed)
# ---------------------------------------------------------------------------

@patch("rss_digest.fetcher.fetch_feed")
def test_fetch_feeds_combines_entries(mock_fetch):
    e1 = Entry(title="A", summary="", link="", published=None, guid="1", feed_name="F1", feed_url="u1")
    e2 = Entry(title="B", summary="", link="", published=None, guid="2", feed_name="F2", feed_url="u2")
    mock_fetch.side_effect = [[e1], [e2]]
    feeds = [{"url": "u1", "name": "F1"}, {"url": "u2", "name": "F2"}]
    result = fetch_feeds(feeds)
    assert len(result) == 2
    assert result[0].title == "A"
    assert result[1].title == "B"


@patch("rss_digest.fetcher.fetch_feed")
def test_fetch_feeds_skips_failed_feed(mock_fetch):
    good = Entry(title="Good", summary="", link="", published=None, guid="g1", feed_name="F1", feed_url="u1")
    mock_fetch.side_effect = [ValueError("network error"), [good]]
    feeds = [{"url": "u1", "name": "F1"}, {"url": "u2", "name": "F2"}]
    result = fetch_feeds(feeds)
    assert len(result) == 1
    assert result[0].title == "Good"


@patch("rss_digest.fetcher.fetch_feed")
def test_fetch_feeds_skips_entries_with_no_url(mock_fetch):
    result = fetch_feeds([{"name": "No URL"}])
    mock_fetch.assert_not_called()
    assert result == []


# ---------------------------------------------------------------------------
# Entry dataclass
# ---------------------------------------------------------------------------

def test_entry_strips_whitespace():
    e = Entry(
        title="  Hello  ",
        summary="  World  ",
        link="http://x",
        published=None,
        guid="g",
        feed_name="F",
        feed_url="u",
    )
    assert e.title == "Hello"
    assert e.summary == "World"
