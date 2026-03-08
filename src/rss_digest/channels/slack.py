"""Send digest messages to a Slack incoming webhook."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def send_slack(webhook_url: str, message: str) -> None:
    """POST *message* to a Slack incoming webhook URL.

    Args:
        webhook_url: Full Slack incoming webhook URL.
        message: Plain text to send. Slack will render basic markdown.

    Raises:
        ValueError: If webhook_url is empty.
        RuntimeError: If the POST fails with a non-200 status.
    """
    if not webhook_url:
        raise ValueError("webhook_url is required")

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Slack webhook returned HTTP {exc.code}: {exc.reason}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to send Slack message: {exc}") from exc

    if status != 200:
        raise RuntimeError(f"Slack webhook returned unexpected status {status}")
