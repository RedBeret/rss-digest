"""Tests for delivery channel modules."""

from __future__ import annotations

import json
import smtplib
import subprocess
from io import BytesIO
from unittest.mock import MagicMock, call, patch

import pytest

from rss_digest.channels.email import send_email
from rss_digest.channels.signal import send_signal
from rss_digest.channels.slack import send_slack


# ---------------------------------------------------------------------------
# signal.py
# ---------------------------------------------------------------------------

@patch("rss_digest.channels.signal.subprocess.run")
def test_send_signal_calls_correct_command(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    send_signal("+15555550100", "+15555550200", "Hello")
    args = mock_run.call_args[0][0]
    assert "signal-cli" in args
    assert "-a" in args
    assert "+15555550100" in args
    assert "+15555550200" in args
    assert "Hello" in args


@patch("rss_digest.channels.signal.subprocess.run")
def test_send_signal_raises_on_nonzero_exit(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="Permission denied")
    with pytest.raises(RuntimeError, match="signal-cli exited with code 1"):
        send_signal("+1", "+2", "msg")


@patch("rss_digest.channels.signal.subprocess.run")
def test_send_signal_uses_custom_cli_path(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    send_signal("+1", "+2", "msg", signal_cli_path="/opt/signal-cli/bin/signal-cli")
    args = mock_run.call_args[0][0]
    assert args[0] == "/opt/signal-cli/bin/signal-cli"


# ---------------------------------------------------------------------------
# slack.py
# ---------------------------------------------------------------------------

@patch("rss_digest.channels.slack.urllib.request.urlopen")
def test_send_slack_posts_correct_payload(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    mock_urlopen.return_value = mock_resp

    send_slack("https://hooks.slack.com/services/FAKE", "Hello Slack")

    request_obj = mock_urlopen.call_args[0][0]
    body = json.loads(request_obj.data.decode("utf-8"))
    assert body["text"] == "Hello Slack"
    assert request_obj.get_header("Content-type") == "application/json"


def test_send_slack_raises_on_empty_webhook():
    with pytest.raises(ValueError, match="webhook_url is required"):
        send_slack("", "msg")


@patch("rss_digest.channels.slack.urllib.request.urlopen")
def test_send_slack_raises_on_http_error(mock_urlopen):
    import urllib.error

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://hooks.slack.com", code=400,
        msg="Bad Request", hdrs=None, fp=None
    )
    with pytest.raises(RuntimeError, match="Slack webhook returned HTTP 400"):
        send_slack("https://hooks.slack.com/services/X", "msg")


# ---------------------------------------------------------------------------
# email.py
# ---------------------------------------------------------------------------

@patch("rss_digest.channels.email.smtplib.SMTP")
def test_send_email_connects_and_sends(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp_cls.return_value = mock_smtp

    send_email(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        from_addr="from@test.com",
        to_addr="to@test.com",
        subject="Test Subject",
        body="Test body",
        password="secret",
    )

    mock_smtp.ehlo.assert_called()
    mock_smtp.starttls.assert_called()
    mock_smtp.login.assert_called_once_with("from@test.com", "secret")
    mock_smtp.sendmail.assert_called_once()
    args = mock_smtp.sendmail.call_args[0]
    assert args[0] == "from@test.com"
    assert args[1] == ["to@test.com"]


@patch("rss_digest.channels.email.smtplib.SMTP")
@patch.dict("os.environ", {"SMTP_PASSWORD": "env-password"})
def test_send_email_reads_password_from_env(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp_cls.return_value = mock_smtp

    send_email("smtp.example.com", 587, "a@b.com", "c@d.com", "Sub", "Body")

    mock_smtp.login.assert_called_once_with("a@b.com", "env-password")


@patch("rss_digest.channels.email.smtplib.SMTP")
def test_send_email_no_login_when_no_password(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp_cls.return_value = mock_smtp

    # No password arg and SMTP_PASSWORD not set
    import os
    os.environ.pop("SMTP_PASSWORD", None)
    send_email("smtp.example.com", 587, "a@b.com", "c@d.com", "Sub", "Body")

    mock_smtp.login.assert_not_called()


@patch("rss_digest.channels.email.smtplib.SMTP")
def test_send_email_raises_on_smtp_error(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.starttls.side_effect = smtplib.SMTPException("TLS failed")
    mock_smtp_cls.return_value = mock_smtp

    with pytest.raises(RuntimeError, match="Failed to send email"):
        send_email("smtp.example.com", 587, "a@b.com", "c@d.com", "Sub", "Body")
