from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

AUTOMATION_SCRIPTS = (
    "scripts/lib.sh",
    "scripts/football_predictor_cli.sh",
    "scripts/daily_morning.sh",
    "scripts/daily_late.sh",
    "scripts/publish_daily_discord.sh",
    "scripts/publish_weekly_score.sh",
    "scripts/refresh_all_leagues.sh",
    "scripts/backfill_season.sh",
    "scripts/train_backtest_all.sh",
    "scripts/train_backtest_ou.sh",
)


def test_daily_automation_scripts_exist_and_do_not_embed_secrets(repo_root: Path) -> None:
    combined = ""
    for relative_path in AUTOMATION_SCRIPTS:
        path = repo_root / relative_path
        assert path.exists()
        assert path.stat().st_mode & 0o111
        combined += path.read_text(encoding="utf-8") + "\n"

    assert "API_FOOTBALL_KEY=" not in combined
    assert "DISCORD_WEBHOOK_URL=" not in combined
    assert "DISCORD_BOT_TOKEN=" not in combined
    assert "discord.com/api/webhooks" not in combined
    secret_scan_text = re.sub(
        r"INCLUDE_PREVIOUS_WEEK_FINALIZATION|include-previous-week-finalization|"
        r"no-include-previous-week-finalization",
        "",
        combined,
    )
    assert not re.search(r"[A-Za-z0-9_-]{32,}", secret_scan_text)
    assert "PYTHONPATH" in (repo_root / "scripts/football_predictor_cli.sh").read_text(
        encoding="utf-8"
    )


def test_daily_scripts_default_to_safe_discord_behavior(repo_root: Path) -> None:
    morning = (repo_root / "scripts/daily_morning.sh").read_text(encoding="utf-8")
    late = (repo_root / "scripts/daily_late.sh").read_text(encoding="utf-8")

    for text in (morning, late):
        assert 'SEND_DISCORD="${SEND_DISCORD:-false}"' in text
        assert 'DRY_RUN="${DRY_RUN:-true}"' in text
        assert "resolve_cli_bin" in text
        assert ".venv/bin/football-predictor" not in text
    assert "predict-today" not in morning
    assert "--json-output" in late
    assert "predict-today" in late
    assert "data/models/v2-late" in late
    assert "data/models/v1" in late
    assert 'REPLACE_PREVIOUS="${REPLACE_PREVIOUS:-true}"' in morning
    assert "scripts/publish_weekly_score.sh" in morning
    publish = (repo_root / "scripts/publish_daily_discord.sh").read_text(encoding="utf-8")
    assert 'REPLACE_PREVIOUS="${REPLACE_PREVIOUS:-true}"' in publish
    assert "--replace-previous" in publish
    weekly = (repo_root / "scripts/publish_weekly_score.sh").read_text(encoding="utf-8")
    assert (
        'INCLUDE_PREVIOUS_WEEK_FINALIZATION="${INCLUDE_PREVIOUS_WEEK_FINALIZATION:-true}"'
        in weekly
    )
    assert 'DRY_RUN="${DRY_RUN:-true}"' in weekly


def test_refresh_and_training_scripts_use_competitions_config(repo_root: Path) -> None:
    refresh = (repo_root / "scripts/refresh_all_leagues.sh").read_text(encoding="utf-8")
    training = (repo_root / "scripts/train_backtest_all.sh").read_text(encoding="utf-8")

    assert "enabled_competitions" in refresh
    assert "competition_dataset_args" in training
    assert "config/competitions.yaml" in refresh
    assert "config/competitions_history.yaml" in training
    assert "config/competitions.yaml" in training
    assert 'REFRESH_TEAMS="${REFRESH_TEAMS:-false}"' in refresh
    assert "ingest-teams --config" in refresh
    assert 'PREDICTION_WINDOW="${PREDICTION_WINDOW:-30m}"' in training
    assert 'MODEL_VERSION="${MODEL_VERSION:-v2-late}"' in training
    assert "data/models/v2-late" in training
    assert "--retrain-v2-model-version" in training
    assert "39" not in refresh
    assert "61" not in refresh
    assert 'REFRESH_DETAILS="${REFRESH_DETAILS:-false}"' in refresh
    assert "DETAILS_DAYS_BACK" in refresh
    assert "DETAILS_STATUSES" in refresh
    assert 'DETAILS_SKIP_IF_COMPLETE="${DETAILS_SKIP_IF_COMPLETE:-true}"' in refresh
    assert "--skip-if-complete" in refresh
    assert "--stop-on-rate-limit" in refresh
    assert "--delay-seconds" in refresh
    assert 'RESOLVE_UNKNOWN_PLAYERS="${RESOLVE_UNKNOWN_PLAYERS:-false}"' in refresh
    assert "resolve-unknown-players" in refresh


def test_backfill_season_generates_season_config_and_refresh_commands(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    backfill_config = tmp_path / "competitions_2024.yaml"
    result = subprocess.run(
        ["scripts/backfill_season.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "SEASON": "2024",
            "BACKFILL_CONFIG": str(backfill_config),
            "DETAILS_LIMIT": "400",
            "DETAILS_DELAY_SECONDS": "3",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    generated = backfill_config.read_text(encoding="utf-8")
    assert "season: 2024" in generated
    assert "key: premier_league_2024" in generated
    assert "reference_key: premier_league" in generated
    assert "fifa_world_cup_2026" not in generated
    assert "Backfill season=2024 from=2024-08-01 to=2025-07-31" in output
    assert "source=config/competitions_history.yaml" in output
    assert f"ingest-teams --config {backfill_config} --refresh-api" in output
    assert "--season 2024" in output
    assert "--from-date 2024-08-01" in output
    assert "--to-date 2025-07-31" in output
    assert "--status FT --status AET --status PEN" in output
    assert "--limit 400" in output
    assert "--delay-seconds 3" in output
    assert "--skip-if-complete" in output
    assert "ingest-odds" not in output
    assert "--league 1 --season 2024" not in output


def test_train_backtest_all_uses_history_config_by_default(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/train_backtest_all.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "Training 1X2 config=config/competitions_history.yaml" in output
    assert output.count("--league 39") == 1
    assert output.count("--league 61") == 1
    assert output.count("--league 78") == 1
    assert output.count("--league 135") == 1
    assert output.count("--league 140") == 1
    for season in ("2022", "2023", "2024", "2025"):
        assert f"--season {season}" in output
    assert re.search(r"--league 1(\s|$)", output) is None


def test_train_backtest_ou_uses_history_config_by_default(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/train_backtest_ou.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "Training O/U config=config/competitions_history.yaml" in output
    assert "ou build-dataset" in output
    assert output.count("--league-id 39") == 1
    assert output.count("--league-id 61") == 1
    assert output.count("--league-id 78") == 1
    assert output.count("--league-id 135") == 1
    assert output.count("--league-id 140") == 1
    for season in ("2022", "2023", "2024", "2025"):
        assert f"--season {season}" in output
    assert "ou train" in output
    assert "ou backtest" in output


def test_refresh_all_leagues_expands_weekly_detail_statuses(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/refresh_all_leagues.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "REFRESH_FIXTURES": "false",
            "REFRESH_STANDINGS": "false",
            "REFRESH_ODDS": "false",
            "REFRESH_DETAILS": "true",
            "DETAILS_ONLY": "statistics events players",
            "DETAILS_DAYS_BACK": "7",
            "DETAILS_STATUSES": "FT AET PEN",
            "DETAILS_LIMIT": "100",
            "DETAILS_DELAY_SECONDS": "3",
            "RESOLVE_UNKNOWN_PLAYERS": "false",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "--days-back 7" in output
    assert "--status FT --status AET --status PEN" in output
    assert "--limit 100" in output
    assert "--skip-if-complete" in output


def test_makefile_exposes_daily_automation_targets(repo_root: Path) -> None:
    text = (repo_root / "Makefile").read_text(encoding="utf-8")

    assert "CLI ?= scripts/football_predictor_cli.sh" in text
    assert "$(CLI) doctor --strict" in text
    assert "$(CLI) data-quality" in text

    for target in (
        "publish-daily-discord:",
        "daily-morning:",
        "daily-late:",
        "refresh-all-leagues:",
        "backfill-season:",
        "train-backtest-all:",
        "train-backtest-ou:",
    ):
        assert target in text


def test_run_predict_today_echo_uses_local_script_without_network(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/run_predict_today.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "DATE": "2026-05-02",
            "WINDOW": "late",
            "REFRESH_DATA": "false",
            "DRY_RUN": "true",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    assert "predict-today --date 2026-05-02 --window late --no-refresh-data --dry-run" in (
        result.stdout.strip()
    )
