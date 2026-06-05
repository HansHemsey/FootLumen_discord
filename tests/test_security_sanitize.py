from __future__ import annotations

from pathlib import Path

from football_predictor.security.sanitize import (
    REDACTED_VALUE,
    contains_sensitive_data,
    sanitize_mapping,
    sanitize_text,
)


def _discord_webhook() -> str:
    return "https://discord.com/api/" + "webhooks/123456789012345678/" + ("a" * 48)


def test_sanitize_text_masks_discord_webhook() -> None:
    webhook = _discord_webhook()

    sanitized = sanitize_text(f"send to {webhook}")

    assert webhook not in sanitized
    assert REDACTED_VALUE in sanitized


def test_sanitize_text_masks_api_key_assignment() -> None:
    key = "abc123DEF456ghi789JKL012mno345"

    sanitized = sanitize_text("API_FOOTBALL_KEY=" + key)

    assert key not in sanitized
    assert sanitized == f"API_FOOTBALL_KEY={REDACTED_VALUE}"


def test_sanitize_mapping_redacts_sensitive_keys_recursively() -> None:
    token = "token-" + ("aB3" * 20)

    sanitized = sanitize_mapping(
        {
            "nested": {
                "authorization": "Bearer " + token,
                "safe": "hello",
            }
        }
    )

    assert sanitized["nested"]["authorization"] == REDACTED_VALUE
    assert sanitized["nested"]["safe"] == "hello"
    assert contains_sensitive_data({"authorization": "Bearer " + token})


def test_business_keys_do_not_trigger_secret_detection() -> None:
    payload = {
        "run_key": "2026-06-11:late:1",
        "session_key": "cdm-2026-session-1",
        "ticket_key": "combo-ticket-1",
    }

    assert not contains_sensitive_data(payload)
    assert sanitize_mapping(payload) == payload


def test_claude_local_settings_are_gitignored(repo_root: Path) -> None:
    ignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")

    assert ".claude/settings.local.json" in ignore_text
