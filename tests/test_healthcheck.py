from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from football_predictor import __version__
from football_predictor.cli import app
from football_predictor.config.settings import Settings, get_settings


def test_settings_include_reference_paths_without_required_secrets(monkeypatch) -> None:
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.api_football_key is None
    assert settings.discord_webhook_url is None
    assert settings.discord_channels_config_path == Path("config/discord_channels.yaml")
    assert settings.discord_webhooks_config_path == Path("config/discord_webhooks.local.yaml")
    assert settings.discord_bot_token is None
    assert settings.discord_api_base_url == "https://discord.com/api/v10"
    assert settings.discord_timeout_seconds == 10.0
    assert settings.api_football_timeout_seconds == 20.0
    assert settings.api_football_max_retries == 2
    assert settings.api_football_raw_snapshot_dir == Path("data/raw/api_football")
    assert settings.competitions_config_path == Path("config/competitions.example.yaml")
    assert settings.api_football_reference_path == Path("docs/api_football_reference.json")
    assert settings.api_football_players_reference_path == Path(
        "docs/api_football_players_reference.json"
    )
    assert settings.api_football_players_cache_path == Path("docs/api_football_players_cache.json")


def test_settings_repr_does_not_expose_secrets() -> None:
    settings = Settings(
        _env_file=None,
        **{
            "API_FOOTBALL_KEY": "synthetic-api-key",
            "DISCORD_WEBHOOK_URL": "https://example.invalid/synthetic-webhook",
        },
    )

    representation = repr(settings)

    assert "synthetic-api-key" not in representation
    assert "synthetic-webhook" not in representation


def test_cli_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_healthcheck_masks_secrets() -> None:
    get_settings.cache_clear()
    runner = CliRunner()
    synthetic_key = "synthetic-api-key-value"
    synthetic_webhook = "https://example.invalid/webhook-value"

    result = runner.invoke(
        app,
        ["healthcheck"],
        env={
            "API_FOOTBALL_KEY": synthetic_key,
            "DISCORD_WEBHOOK_URL": synthetic_webhook,
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Football Predictor healthcheck" in result.stdout
    assert "Version:" in result.stdout
    assert "docs/api_football_reference.json" in result.stdout
    assert "API key configured: yes, hash=" in result.stdout
    assert "Discord webhook configured: yes, hash=" in result.stdout
    assert synthetic_key not in result.stdout
    assert synthetic_webhook not in result.stdout


def test_live_ingestion_commands_require_explicit_refresh_flag() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["ingest-leagues"])

    assert result.exit_code == 2
    assert "--refresh-api" in result.stdout
