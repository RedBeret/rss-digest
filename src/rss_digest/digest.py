"""Format feed entries into a human-readable digest."""

from __future__ import annotations

from datetime import datetime, timezone
from textwrap import shorten
from typing import Optional

from .fetcher import Entry


def _truncate_summary(text: str, max_chars: int = 200) -> str:
    """Return a clean truncated version of a summary."""
    # Strip HTML-ish tags (crude but avoids an html.parser dependency path)
    import re

    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return shorten(clean, width=max_chars, placeholder="…")


def format_digest(entries: list[Entry], max_chars: int = 4000) -> str:
    """Format entries as a plain-text digest string.

    Args:
        entries: List of Entry objects to include.
        max_chars: Soft cap on total message length. Entries are added until
                   the cap would be exceeded, then the rest are dropped.

    Returns:
        A plain-text string suitable for sending via Signal, Slack, or email.
    """
    if not entries:
        return "No new entries in your feeds."

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [f"📰 RSS Digest — {today}", ""]

    # Group by feed
    by_feed: dict[str, list[Entry]] = {}
    for entry in entries:
        by_feed.setdefault(entry.feed_name, []).append(entry)

    body_parts: list[str] = []
    for feed_name, feed_entries in by_feed.items():
        section: list[str] = [f"── {feed_name} ──"]
        for entry in feed_entries:
            title_line = f"• {entry.title}"
            if entry.link:
                title_line += f"\n  {entry.link}"
            if entry.summary:
                summary_line = "  " + _truncate_summary(entry.summary)
                title_line += f"\n{summary_line}"
            section.append(title_line)
        body_parts.append("\n".join(section))

    body = "\n\n".join(body_parts)

    # Trim to max_chars
    header = "\n".join(lines)
    full = header + "\n" + body
    if len(full) > max_chars:
        full = full[: max_chars - 4] + "\n…"

    return full


def format_digest_ai(
    entries: list[Entry],
    model: Optional[str] = None,
    max_chars: int = 4000,
) -> str:
    """Format entries using Claude (if available), falling back to plain text.

    Requires the ``anthropic`` package and an ANTHROPIC_API_KEY env var.
    If not available, gracefully falls back to :func:`format_digest`.
    """
    try:
        import anthropic  # noqa: F401 — check import only
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ImportError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=api_key)
        chosen_model = model or "claude-haiku-4-5"

        bullet_list = "\n".join(
            f"- [{e.feed_name}] {e.title}: {_truncate_summary(e.summary, 300)}"
            for e in entries[:30]  # cap to avoid huge prompts
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prompt = (
            f"You are writing a brief daily news digest for {today}. "
            "Summarize the following stories in 3-5 sentences, grouped by topic. "
            "Be concise and informative. No filler. Plain text only.\n\n"
            f"{bullet_list}"
        )

        message = client.messages.create(
            model=chosen_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = message.content[0].text.strip()
        return f"📰 AI Digest — {today}\n\n{summary}"

    except Exception:
        return format_digest(entries, max_chars=max_chars)
