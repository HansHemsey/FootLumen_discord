from __future__ import annotations

from pathlib import Path

from scripts.security_scan import scan_paths


def test_security_scan_allows_empty_example_values(tmp_path: Path) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        "\n".join(
            [
                "API_FOOTBALL_KEY=",
                "DISCORD_BOT_TOKEN=",
                "DISCORD_WEBHOOK_URL=",
                "webhook_url: REPLACE_WITH_WEBHOOK_URL",
            ]
        ),
        encoding="utf-8",
    )

    assert scan_paths([env_example], tmp_path) == []


def test_security_scan_detects_discord_webhook(tmp_path: Path) -> None:
    webhook = "https://discord.com/api/" + "webhooks/123456789012345678/" + ("a" * 40)
    candidate = tmp_path / "config.py"
    candidate.write_text(f'WEBHOOK = "{webhook}"\n', encoding="utf-8")

    findings = scan_paths([candidate], tmp_path)

    assert len(findings) == 1
    assert findings[0].reason == "discord_webhook_url"


def test_security_scan_detects_non_empty_api_key(tmp_path: Path) -> None:
    candidate = tmp_path / "settings.env"
    candidate.write_text("API_FOOTBALL_KEY=" + "abc123def456ghi789" + "\n", encoding="utf-8")

    findings = scan_paths([candidate], tmp_path)

    assert len(findings) == 1
    assert findings[0].reason == "sensitive_env_assignment"
