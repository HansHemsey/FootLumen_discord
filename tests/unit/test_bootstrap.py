from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import football_predictor
from football_predictor.cli import app
from football_predictor.config.settings import Settings, get_settings


def test_package_imports_with_version() -> None:
    assert football_predictor.__version__


def test_settings_default_reference_paths() -> None:
    settings = Settings(_env_file=None)

    assert settings.api_football_timeout_seconds == 20.0
    assert settings.api_football_max_retries == 2
    assert settings.api_football_raw_snapshot_dir == Path("data/raw/api_football")
    assert settings.api_football_reference_path == Path("docs/api_football_reference.json")
    assert settings.api_football_players_reference_path == Path(
        "docs/api_football_players_reference.json"
    )
    assert settings.api_football_players_cache_path == Path(
        "docs/api_football_players_cache.json"
    )


def test_reference_paths_exist(repo_root: Path) -> None:
    expected_paths = [
        repo_root / "docs" / "api_football_reference.md",
        repo_root / "docs" / "api_football_reference.json",
        repo_root / "docs" / "api_football_players_reference.md",
        repo_root / "docs" / "api_football_players_reference.json",
        repo_root / "docs" / "api_football_players_cache.json",
    ]

    assert all(path.exists() for path in expected_paths)


def test_doctor_cli_masks_configured_secret_values() -> None:
    get_settings.cache_clear()
    runner = CliRunner()
    synthetic_key = "synthetic-api-key-value"
    synthetic_webhook = "https://example.invalid/webhook-value"

    result = runner.invoke(
        app,
        ["doctor"],
        env={
            "API_FOOTBALL_KEY": synthetic_key,
            "DISCORD_WEBHOOK_URL": synthetic_webhook,
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Version:" in result.stdout
    assert "docs/api_football_reference.json" in result.stdout
    assert "API key configured: yes, hash=" in result.stdout
    assert "Discord webhook configured: yes, hash=" in result.stdout
    assert synthetic_key not in result.stdout
    assert synthetic_webhook not in result.stdout
