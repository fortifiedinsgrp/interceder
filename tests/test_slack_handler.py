"""Tests for Slack event normalization into Message objects."""
from __future__ import annotations

from interceder.gateway.slack_handler import normalize_slack_event


def test_normalize_text_message() -> None:
    event = {
        "type": "message",
        "user": "U1234",
        "text": "hello interceder",
        "ts": "1700000000.123456",
        "channel": "D01234",
        "channel_type": "im",
    }
    msg = normalize_slack_event(event)
    assert msg is not None
    assert msg.source == "slack"
    assert msg.kind == "text"
    assert msg.content == "hello interceder"
    assert msg.user_id == "U1234"
    assert msg.metadata["slack_ts"] == "1700000000.123456"
    assert msg.metadata["slack_channel"] == "D01234"
    assert msg.correlation_id.startswith("slack:")


def test_normalize_ignores_bot_messages() -> None:
    event = {
        "type": "message",
        "subtype": "bot_message",
        "text": "bot reply",
        "ts": "1700000000.999",
        "channel": "D01234",
    }
    msg = normalize_slack_event(event)
    assert msg is None


def test_normalize_ignores_message_changed() -> None:
    event = {
        "type": "message",
        "subtype": "message_changed",
        "channel": "D01234",
    }
    msg = normalize_slack_event(event)
    assert msg is None


def test_normalize_with_files() -> None:
    event = {
        "type": "message",
        "user": "U1234",
        "text": "look at this",
        "ts": "1700000001.000",
        "channel": "D01234",
        "channel_type": "im",
        "files": [
            {
                "id": "F01",
                "name": "screenshot.png",
                "mimetype": "image/png",
                "url_private_download": "https://files.slack.com/...",
            }
        ],
    }
    msg = normalize_slack_event(event)
    assert msg is not None
    assert len(msg.metadata["slack_files"]) == 1
    assert msg.metadata["slack_files"][0]["id"] == "F01"
