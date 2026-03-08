"""Command-line interface for rss-digest."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from .channels.email import send_email
from .channels.signal import send_signal
from .channels.slack import send_slack
from .digest import format_digest, format_digest_ai
from .fetcher import fetch_feeds
from .store import DigestStore


def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise click.ClickException(f"Config file not found: {config_path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _get_store(config: dict) -> DigestStore:
    db_path_str = config.get("db_path")
    db_path = Path(db_path_str) if db_path_str else None
    return DigestStore(db_path=db_path)


@click.group()
@click.version_option()
def cli() -> None:
    """rss-digest — Fetch feeds, deduplicate, and deliver summaries."""


@cli.command()
@click.option("--config", "-c", required=True, help="Path to config YAML file.")
def fetch(config: str) -> None:
    """Fetch all configured feeds and show new entries."""
    cfg = _load_config(config)
    feed_configs = cfg.get("feeds", [])
    if not feed_configs:
        click.echo("No feeds configured.")
        return

    click.echo(f"Fetching {len(feed_configs)} feed(s)…")
    entries = fetch_feeds(feed_configs)

    with _get_store(cfg) as store:
        new_entries = store.add_entries(entries)

    click.echo(f"Total fetched: {len(entries)}  |  New: {len(new_entries)}")
    for entry in new_entries:
        pub = entry.published.strftime("%Y-%m-%d") if entry.published else "unknown"
        click.echo(f"  [{entry.feed_name}] {entry.title} ({pub})")


@cli.command()
@click.option("--config", "-c", required=True, help="Path to config YAML file.")
@click.option(
    "--channel",
    type=click.Choice(["signal", "slack", "email"]),
    default=None,
    help="Delivery channel (overrides config default).",
)
@click.option("--force", is_flag=True, help="Send even if a digest was already sent today.")
@click.option("--dry-run", is_flag=True, help="Print digest without sending.")
def digest(config: str, channel: Optional[str], force: bool, dry_run: bool) -> None:
    """Fetch new entries, format a digest, and send it to a channel."""
    cfg = _load_config(config)
    feed_configs = cfg.get("feeds", [])
    if not feed_configs:
        raise click.ClickException("No feeds configured.")

    target_channel = channel or cfg.get("default_channel")
    if not target_channel and not dry_run:
        raise click.ClickException(
            "No channel specified. Use --channel or set default_channel in config."
        )

    entries = fetch_feeds(feed_configs)

    with _get_store(cfg) as store:
        if target_channel and not force and store.has_digest_today(target_channel):
            click.echo(f"Digest already sent to {target_channel!r} today. Use --force to send again.")
            return

        new_entries = store.add_entries(entries)
        max_entries = cfg.get("max_entries", 10)
        selected = new_entries[:max_entries]

        use_ai = cfg.get("ai_summary", False)
        if use_ai:
            text = format_digest_ai(selected)
        else:
            text = format_digest(selected)

        if dry_run:
            click.echo("── Digest preview ──")
            click.echo(text)
            return

        _deliver(cfg, target_channel, text)
        store.record_digest(target_channel)
        click.echo(f"Digest sent to {target_channel!r} ({len(selected)} entries).")


def _deliver(cfg: dict, channel: str, text: str) -> None:
    """Route text to the chosen channel using config settings."""
    channels_cfg = cfg.get("channels", {})

    if channel == "signal":
        sig_cfg = channels_cfg.get("signal", {})
        account = sig_cfg.get("account") or ""
        recipient = sig_cfg.get("recipient") or ""
        if not account or not recipient:
            raise click.ClickException(
                "Signal channel requires channels.signal.account and .recipient in config."
            )
        send_signal(account, recipient, text)

    elif channel == "slack":
        slack_cfg = channels_cfg.get("slack", {})
        webhook_url = slack_cfg.get("webhook_url") or ""
        if not webhook_url:
            raise click.ClickException(
                "Slack channel requires channels.slack.webhook_url in config."
            )
        send_slack(webhook_url, text)

    elif channel == "email":
        email_cfg = channels_cfg.get("email", {})
        required = ("smtp_host", "smtp_port", "from", "to")
        missing = [k for k in required if not email_cfg.get(k)]
        if missing:
            raise click.ClickException(
                f"Email channel missing config keys: {', '.join(missing)}"
            )
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        send_email(
            smtp_host=email_cfg["smtp_host"],
            smtp_port=int(email_cfg["smtp_port"]),
            from_addr=email_cfg["from"],
            to_addr=email_cfg["to"],
            subject=f"RSS Digest — {today}",
            body=text,
        )
    else:
        raise click.ClickException(f"Unknown channel: {channel!r}")


@cli.command("list")
@click.option("--config", "-c", required=True, help="Path to config YAML file.")
def list_feeds(config: str) -> None:
    """List all configured feeds."""
    cfg = _load_config(config)
    feeds = cfg.get("feeds", [])
    if not feeds:
        click.echo("No feeds configured.")
        return
    click.echo(f"{len(feeds)} configured feed(s):")
    for feed in feeds:
        name = feed.get("name", "(unnamed)")
        url = feed.get("url", "(no url)")
        click.echo(f"  {name}: {url}")


@cli.command()
@click.option("--last", "-n", default=7, show_default=True, help="Number of recent digests to show.")
@click.option("--config", "-c", default=None, help="Path to config YAML (for custom db_path).")
def history(last: int, config: Optional[str]) -> None:
    """Show recent digest history."""
    cfg = _load_config(config) if config else {}
    with _get_store(cfg) as store:
        records = store.recent_digests(limit=last)
    if not records:
        click.echo("No digest history yet.")
        return
    click.echo(f"Last {min(last, len(records))} digest(s):")
    for rec in records:
        click.echo(f"  {rec['date']}  channel={rec['channel']}  sent_at={rec['sent_at']}")


if __name__ == "__main__":
    cli()
