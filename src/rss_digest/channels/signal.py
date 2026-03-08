"""Send digest messages via signal-cli."""

from __future__ import annotations

import subprocess
from typing import Optional


def send_signal(
    account: str,
    recipient: str,
    message: str,
    signal_cli_path: str = "signal-cli",
) -> None:
    """Send *message* from *account* to *recipient* using signal-cli.

    Uses the CLI directly (not the daemon) for maximum portability.

    Args:
        account: Your registered Signal number, e.g. "+15555550100".
        recipient: Recipient's Signal number, e.g. "+15555550200".
        message: Text to send.
        signal_cli_path: Path to signal-cli binary.

    Raises:
        RuntimeError: If signal-cli returns a non-zero exit code.
        FileNotFoundError: If signal-cli is not found on PATH.
    """
    cmd = [
        signal_cli_path,
        "--output", "json",
        "-a", account,
        "send",
        "-m", message,
        recipient,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"signal-cli exited with code {result.returncode}: {stderr}"
        )
