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
    "scripts/daily_ou.sh",
    "scripts/weekly_ingestion.sh",
    "scripts/install_prod_cron.sh",
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
    assert 'PREDICTION_ENGINE="${PREDICTION_ENGINE:-v3}"' in late
    assert "predict-today-v3" in late
    assert "--production-mode" in late
    assert "predict-today" in late
    assert "data/models/v2-late" in late
    assert "data/models/v3" in late
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
    daily_ou = (repo_root / "scripts/daily_ou.sh").read_text(encoding="utf-8")
    assert 'RUN_WINDOW="${WINDOW:-late}"' in daily_ou
    assert "--window" in daily_ou


def test_prod_crontab_runs_publication_scripts_with_prod_flags(repo_root: Path) -> None:
    text = (repo_root / "config/prod.crontab").read_text(encoding="utf-8")

    assert "PROJECT=/Users/yanisruel/Documents/ProBet_discord" in text
    assert "/usr/bin/lockf -t 0" in text
    assert 'cd "$PROJECT"' in text
    assert "scripts/weekly_ingestion.sh" in text
    assert "SAVE_RAW=true DRY_RUN=false scripts/weekly_ingestion.sh" in text
    assert "SEND_DISCORD=true DRY_RUN=false PUBLISH_DISCORD=true" in text
    assert "scripts/daily_morning.sh" in text
    assert "scripts/publish_match_analyses.sh" in text
    assert "scripts/daily_late.sh" in text
    assert "PREDICTION_ENGINE=v3 WINDOW=late" in text
    assert "scripts/daily_ou.sh" in text
    assert "scripts/publish_match_results.sh" in text
    assert "scripts/publish_weekly_score.sh" in text
    assert "DRY_RUN=true" not in text
    assert "PRINT_ONLY=true" not in text
    assert "config/discord_webhooks.local.yaml" not in text


def test_worldcup_prod_crontab_is_cdm_only(repo_root: Path) -> None:
    text = (repo_root / "config/prod_worldcup.crontab").read_text(encoding="utf-8")

    assert "CONFIG_WC=config/competitions_worldcup.yaml" in text
    assert "football-predictor worldcup-run-daily" in text
    assert "--window late" in text
    assert "--refresh-data" in text
    assert "--send-discord" in text
    assert "--no-dry-run" in text
    assert "REFRESH_FIXTURES=true REFRESH_STANDINGS=true REFRESH_ODDS=false" in text
    assert "ingest-player-squads --config \"$CONFIG_WC\" --refresh-api" in text
    assert "DETAILS_ONLY=\"statistics events lineups players injuries predictions\"" in text
    assert "scripts/daily_late.sh" not in text
    assert "scripts/daily_ou.sh" not in text
    assert "scripts/publish_match_analyses.sh" not in text
    assert "PREDICTION_ENGINE=v3" not in text


def test_prod_cron_installer_uses_versioned_crontab(repo_root: Path) -> None:
    text = (repo_root / "scripts/install_prod_cron.sh").read_text(encoding="utf-8")

    assert 'CRONTAB_FILE="${CRONTAB_FILE:-config/prod.crontab}"' in text
    assert 'crontab "$CRONTAB_FILE"' in text
    assert "crontab -l" in text
    assert "logs/cron" in text


def test_weekly_ingestion_echo_generates_seven_future_dates(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "competitions.yaml"
    config_path.write_text(
        """
competitions:
  - key: synthetic_league
    league_id: -100
    season: 2026
    name: Synthetic League
    enabled: true
  - key: disabled_league
    league_id: -200
    season: 2026
    name: Disabled League
    enabled: false
""".strip(),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["scripts/weekly_ingestion.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "DATE": "2026-05-04",
            "CONFIG": str(config_path),
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "Weekly fixture ingestion J+7 from date=2026-05-04" in output
    assert output.count("ingest-fixtures --date") == 7
    assert "--date 2026-05-04 --league -100 --season 2026 --refresh-api" in output
    assert "--date 2026-05-10 --league -100 --season 2026 --refresh-api" in output
    assert "--league -200" not in output


def test_daily_ou_echo_uses_late_window(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/daily_ou.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "DATE": "2026-05-02",
            "REFRESH_DATA": "false",
            "DRY_RUN": "true",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "ou run-daily --date 2026-05-02 --window late" in output
    assert "--dry-run" in output


def test_daily_late_echo_defaults_to_v3_production_command(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/daily_late.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "DATE": "2026-05-02",
            "WINDOW": "late",
            "REFRESH_DATA": "false",
            "DRY_RUN": "true",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "predict-today-v3 --date 2026-05-02 --window late" in output
    assert "--model-dir data/models/v3" in output
    assert "--v2-model-dir data/models/v2-late" in output
    assert "--production-mode" in output
    assert "--json-output reports/daily/2026-05-02_late_v3_summary.json" in output
    assert "--no-refresh-data" in output
    assert "--dry-run" in output
    assert "Daily late summary written to reports/daily/2026-05-02_late_v3_summary.json" in output


def test_daily_late_echo_uses_v2_rollback_command(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/daily_late.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "PREDICTION_ENGINE": "v2",
            "DATE": "2026-05-02",
            "WINDOW": "late",
            "REFRESH_DATA": "false",
            "DRY_RUN": "true",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "predict-today --date 2026-05-02 --window late" in output
    assert "predict-today-v3" not in output
    assert "--production-mode" not in output
    assert "--json-output reports/daily/2026-05-02_late_summary.json" in output
    assert "--no-refresh-data" in output
    assert "--dry-run" in output


def test_daily_late_echo_passes_refresh_to_worldcup(repo_root: Path) -> None:
    result = subprocess.run(
        ["scripts/daily_late.sh"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            "FOOTBALL_PREDICTOR_BIN": "echo",
            "PYTHON_BIN": sys.executable,
            "DATE": "2026-06-11",
            "WINDOW": "late",
            "REFRESH_DATA": "true",
            "SAVE_RAW": "true",
            "DRY_RUN": "true",
            "WORLD_CUP_1X2_ENABLED": "true",
            "PATH": "/usr/bin:/bin",
        },
        text=True,
    )

    output = result.stdout
    assert "worldcup-run-daily --date 2026-06-11 --window late" in output
    assert "--model-dir data/models/worldcup-1x2" in output
    assert "--json-output reports/daily/2026-06-11_worldcup_late_summary.json" in output
    assert "--refresh-data" in output
    assert "--save-raw" in output
    assert "--dry-run" in output


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
