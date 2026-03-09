# rss-digest

[![CI](https://github.com/RedBeret/rss-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/RedBeret/rss-digest/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rss-digest.svg)](https://pypi.org/project/rss-digest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Subscribe to RSS feeds. Get a daily digest delivered to Signal, Slack, or email. No cloud, no subscription.**

RSS is back — people follow dozens of feeds but don't have time to read everything. `rss-digest` fetches your feeds on a schedule, deduplicates entries across runs, formats the top stories, and pushes a clean summary to wherever you want it.

## Why this over just using an RSS reader?

- **Delivery push, not pull** — digest comes to you, not the other way around
- **Deduplication** — stories you've already seen don't repeat across runs
- **Self-hosted** — your feeds, your data, your server
- **Scriptable** — run via cron, systemd timer, or Docker
- **Multi-channel** — same digest to Signal, Slack, and email with one command

## Install

```bash
pip install rss-digest
```

Or from source:

```bash
git clone https://github.com/RedBeret/rss-digest.git
cd rss-digest
pip install -e .
```

## Quick Start

**1. Create a config file:**

```yaml
# config.yaml
feeds:
  - url: "https://hnrss.org/frontpage"
    name: "Hacker News"
  - url: "https://feeds.arstechnica.com/arstechnica/index"
    name: "Ars Technica"

channels:
  signal:
    account: "+15555550100"
    recipient: "+15555550200"

max_entries: 10
```

**2. Fetch new entries:**

```bash
rss-digest fetch --config config.yaml
```

**3. Send a digest:**

```bash
rss-digest digest --config config.yaml --channel signal
```

## Commands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch all feeds, show new entries |
| `digest` | Fetch + format + send to a channel |
| `list` | List configured feeds |
| `history` | Show recent digest history |

```bash
# Show what's new (no send)
rss-digest fetch --config config.yaml

# Send to Slack
rss-digest digest --config config.yaml --channel slack

# Send to email
rss-digest digest --config config.yaml --channel email

# View history
rss-digest history --last 7

# List feeds
rss-digest list --config config.yaml
```

## Config Reference

```yaml
feeds:
  - url: "https://hnrss.org/frontpage"
    name: "Hacker News"          # Display name in digest
  - url: "https://feeds.arstechnica.com/arstechnica/index"
    name: "Ars Technica"

channels:
  signal:
    account: "+15555550100"      # Your signal-cli account number
    recipient: "+15555550200"    # Who to send to

  slack:
    webhook_url: "https://hooks.slack.com/services/..."

  email:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    from: "you@gmail.com"
    to: "you@gmail.com"
    # Set SMTP_PASSWORD env var — never put it in config

max_entries: 10      # Max stories per digest
ai_summary: false    # Optional: use Claude for summaries
```

## Channels

### Signal

Requires [signal-cli](https://github.com/AsamK/signal-cli) installed and registered:

```bash
# Install signal-cli, then register your number
signal-cli -u +15555550100 register
signal-cli -u +15555550100 verify <code>
```

### Slack

Create an [incoming webhook](https://api.slack.com/messaging/webhooks) in your Slack workspace. Set `webhook_url` in config.

### Email

Set `SMTP_PASSWORD` environment variable. Works with Gmail (use an App Password), Fastmail, or any SMTP server.

## Example Output

```
📰 Daily Digest — 2026-03-08

── Hacker News ──────────────────────────────────────────────
• Ask HN: What's your morning reading routine? (432 points)
  https://news.ycombinator.com/item?id=39123456

• Show HN: I built a tool to track RSS feeds from the terminal (87 points)
  https://news.ycombinator.com/item?id=39124001

• The unreasonable effectiveness of plain text (211 points)
  https://hnrss.org/item/39124200

── Ars Technica ─────────────────────────────────────────────
• EU regulators open investigation into major cloud providers
  https://arstechnica.com/tech-policy/2026/03/eu-cloud-probe/

• Rust achieves memory safety without garbage collection overhead
  https://arstechnica.com/information-technology/2026/03/rust-memory/

5 new entries across 2 feeds. Digest sent via Signal.
```

## Run on a Schedule

**Cron (daily at 7am):**
```cron
0 7 * * * /usr/local/bin/rss-digest digest --config /home/user/rss-digest.yaml --channel signal
```

**systemd timer** (`~/.config/systemd/user/rss-digest.timer`):
```ini
[Unit]
Description=RSS Digest daily run

[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## Docker

Self-hosted deployment with persistent dedup database:

```bash
# Clone and build
git clone https://github.com/RedBeret/rss-digest.git
cd rss-digest

# Create your config
cp examples/config.example.yaml config.yaml
# Edit config.yaml with your feeds and channel settings

# Build image
docker build -t rss-digest .

# Run a digest (one-shot)
docker run --rm \
  -v $(pwd)/config.yaml:/config/config.yaml:ro \
  -v rss-digest-data:/data \
  -e SMTP_PASSWORD="${SMTP_PASSWORD}" \
  rss-digest digest --config /config/config.yaml --channel slack

# Using docker compose (with volume persistence)
docker compose run --rm rss-digest digest --config /config/config.yaml --channel signal
```

**Add to host cron for daily digests:**
```cron
0 7 * * * docker compose -f /home/user/rss-digest/docker-compose.yml run --rm rss-digest digest --config /config/config.yaml --channel signal
```

## Development

```bash
git clone https://github.com/RedBeret/rss-digest.git
cd rss-digest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## License

MIT
