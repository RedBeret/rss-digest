"""Send digest messages via SMTP email."""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional


def send_email(
    smtp_host: str,
    smtp_port: int,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    password: Optional[str] = None,
) -> None:
    """Send an email via SMTP with STARTTLS.

    The password may be provided as an argument or read from the
    ``SMTP_PASSWORD`` environment variable. If neither is set and the
    SMTP server requires authentication, the send will fail.

    Args:
        smtp_host: SMTP server hostname, e.g. "smtp.gmail.com".
        smtp_port: SMTP port (typically 587 for STARTTLS).
        from_addr: Sender address.
        to_addr: Recipient address.
        subject: Email subject line.
        body: Plain-text email body.
        password: SMTP password. Falls back to SMTP_PASSWORD env var.

    Raises:
        RuntimeError: On SMTP or authentication failures.
    """
    resolved_password = password or os.environ.get("SMTP_PASSWORD", "")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if resolved_password:
                server.login(from_addr, resolved_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
    except smtplib.SMTPException as exc:
        raise RuntimeError(f"Failed to send email: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"SMTP connection failed: {exc}") from exc
