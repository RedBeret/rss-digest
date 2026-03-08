"""Tests for rss_digest.store (SQLite dedup store)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from rss_digest.fetcher import Entry
from rss_digest.store import DigestStore


def _entry(guid: str, title: str = "Title", feed_url: str = "http://feed.example/rss") -> Entry:
    return Entry(
        title=title,
        summary="Some summary",
        link=f"http://example.com/{guid}",
        published=datetime(2026, 3, 8, tzinfo=timezone.utc),
        guid=guid,
        feed_name="Test Feed",
        feed_url=feed_url,
    )


@pytest.fixture
def store(tmp_path: Path) -> DigestStore:
    db = tmp_path / "test.db"
    s = DigestStore(db_path=db)
    yield s
    s.close()


# ---------------------------------------------------------------------------
# add_entries / deduplication
# ---------------------------------------------------------------------------

def test_add_entries_returns_new_entries(store):
    entries = [_entry("g1"), _entry("g2")]
    new = store.add_entries(entries)
    assert len(new) == 2


def test_add_entries_deduplicates_same_guid(store):
    entry = _entry("g1")
    first = store.add_entries([entry])
    second = store.add_entries([entry])
    assert len(first) == 1
    assert len(second) == 0  # already seen


def test_add_entries_same_guid_different_feed_are_unique(store):
    e1 = _entry("g1", feed_url="http://feed1.com/rss")
    e2 = _entry("g1", feed_url="http://feed2.com/rss")
    new = store.add_entries([e1, e2])
    assert len(new) == 2


def test_add_entries_empty_list(store):
    assert store.add_entries([]) == []


def test_add_entries_increments_count(store):
    store.add_entries([_entry("a"), _entry("b"), _entry("c")])
    assert store.entry_count() == 3


def test_add_entries_second_batch_returns_only_new(store):
    store.add_entries([_entry("a"), _entry("b")])
    # "b" is old, "c" is new
    new = store.add_entries([_entry("b"), _entry("c")])
    assert len(new) == 1
    assert new[0].guid == "c"


# ---------------------------------------------------------------------------
# digest history
# ---------------------------------------------------------------------------

def test_has_digest_today_false_initially(store):
    assert store.has_digest_today("signal") is False


def test_record_and_check_digest_today(store):
    store.record_digest("signal")
    assert store.has_digest_today("signal") is True


def test_different_channels_are_independent(store):
    store.record_digest("signal")
    assert store.has_digest_today("slack") is False


def test_recent_digests_returns_records(store):
    store.record_digest("signal")
    store.record_digest("slack")
    records = store.recent_digests(limit=10)
    assert len(records) == 2
    channels = {r["channel"] for r in records}
    assert channels == {"signal", "slack"}


def test_recent_digests_respects_limit(store):
    for _ in range(5):
        store.record_digest("signal")
    records = store.recent_digests(limit=3)
    assert len(records) == 3


def test_recent_digests_empty_initially(store):
    assert store.recent_digests() == []


# ---------------------------------------------------------------------------
# entry_count
# ---------------------------------------------------------------------------

def test_entry_count_zero_initially(store):
    assert store.entry_count() == 0


def test_entry_count_after_insert(store):
    store.add_entries([_entry("x"), _entry("y")])
    assert store.entry_count() == 2


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_store_context_manager(tmp_path):
    db = tmp_path / "ctx.db"
    with DigestStore(db_path=db) as store:
        store.add_entries([_entry("ctx1")])
    # Re-open and verify persistence
    with DigestStore(db_path=db) as store2:
        assert store2.entry_count() == 1
