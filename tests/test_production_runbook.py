from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.world_cup_combos.config import load_world_cup_combo_config

EXECUTE_SCRIPT_HELP = (
    "scripts/ingest_national_results.py",
    "scripts/compute_national_elo.py",
    "scripts/ingest_fifa_rankings.py",
    "scripts/build_worldcup_feature_matrix.py",
    "scripts/sync_worldcup_odds_snapshots.py",
    "scripts/build_group_incentive_features.py",
    "scripts/build_squad_strength_features.py",
    "scripts/worldcup_coverage_report.py",
    "scripts/run_worldcup_combos.py",
    "scripts/publish_worldcup_combos.py",
    "scripts/lock_worldcup_combos.py",
    "scripts/settle_worldcup_combos.py",
    "scripts/maintenance_worldcup_combo_snapshots.py",
)


def test_worldcup_combo_example_config_is_safe_by_default(repo_root: Path) -> None:
    config = load_world_cup_combo_config(repo_root / "config/worldcup_combos.example.yaml")

    assert config.enabled is False
    assert config.staff_only_shadow_mode is True
    assert config.public_channel_key == "combines"
    assert config.publish_no_bet_public is False
    assert config.allow_public_matchday3 is False
    assert config.allow_public_knockout is False


def test_worldcup_prod_example_crontab_documents_explicit_execute(repo_root: Path) -> None:
    text = (repo_root / "config/prod_worldcup.example.crontab").read_text(encoding="utf-8")

    assert "config/worldcup_combos.yaml" in text
    assert "staff_only_shadow_mode: false" not in text
    assert 'worldcup-combos-run --config "$COMBOS_CONFIG" --execute' in text
    assert 'scripts/lock_worldcup_combos.py --config "$COMBOS_CONFIG" --execute' in text
    assert 'worldcup-combos-publish --config "$COMBOS_CONFIG" --execute' in text
    assert 'scripts/settle_worldcup_combos.py --config "$COMBOS_CONFIG" --execute' in text
    assert "config/discord_webhooks.local.yaml" not in text
    assert "discord.com/api/webhooks" not in text


def test_dangerous_worldcup_scripts_expose_execute_and_dry_run(repo_root: Path) -> None:
    env = {"PYTHONPATH": str(repo_root / "src"), "PATH": "/usr/bin:/bin"}

    for relative_path in EXECUTE_SCRIPT_HELP:
        result = subprocess.run(
            [sys.executable, str(repo_root / relative_path), "--help"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )
        help_text = (result.stdout + result.stderr).replace("-\n", "-").replace("\n", " ")
        assert "--execute" in help_text, relative_path
        assert "dry-run" in help_text.lower(), relative_path


def test_worldcup_combos_publish_dry_run_disabled_config_does_not_publish(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "worldcup-combos-publish",
            "--config",
            str(repo_root / "config/worldcup_combos.example.yaml"),
            "--dry-run",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'disabled_combos.db'}",
            "DISCORD_WEBHOOK_URL": "",
            "DISCORD_CHANNELS_CONFIG_PATH": "config/discord_channels.example.yaml",
            "DISCORD_WEBHOOKS_CONFIG_PATH": "config/discord_webhooks.example.yaml",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert '"enabled": false' in result.stdout
    assert "worldcup_combos disabled" in result.stdout
    assert "https://" not in result.stdout


def test_worldcup_combos_publish_dry_run_missing_tables_is_noop(tmp_path: Path) -> None:
    get_settings.cache_clear()
    config = tmp_path / "worldcup_combos.yaml"
    config.write_text(
        "\n".join(
            [
                "enabled: true",
                "competition_key: fifa_world_cup_2026",
                "staff_only_shadow_mode: true",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["worldcup-combos-publish", "--config", str(config), "--dry-run"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'missing_combo_tables.db'}",
            "DISCORD_WEBHOOK_URL": "",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "combo tables missing" in result.stdout
    assert "https://" not in result.stdout


def test_worldcup_combos_publish_execute_missing_tables_fails(tmp_path: Path) -> None:
    get_settings.cache_clear()
    config = tmp_path / "worldcup_combos.yaml"
    config.write_text(
        "\n".join(
            [
                "enabled: true",
                "competition_key: fifa_world_cup_2026",
                "staff_only_shadow_mode: true",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["worldcup-combos-publish", "--config", str(config), "--execute"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'missing_combo_execute_tables.db'}",
            "DISCORD_WEBHOOK_URL": "",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 2
    assert "combo tables missing" in result.stdout
    assert "https://" not in result.stdout


def test_combo_lock_and_settle_dry_run_missing_tables_are_noop(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    config = tmp_path / "worldcup_combos.yaml"
    config.write_text("enabled: true\ncompetition_key: fifa_world_cup_2026\n", encoding="utf-8")
    env = {
        "PYTHONPATH": str(repo_root / "src"),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'missing_combo_script_tables.db'}",
        "PATH": "/usr/bin:/bin",
    }

    for relative_path in ("scripts/lock_worldcup_combos.py", "scripts/settle_worldcup_combos.py"):
        result = subprocess.run(
            [sys.executable, str(repo_root / relative_path), "--config", str(config)],
            cwd=repo_root,
            capture_output=True,
            env=env,
            text=True,
        )
        assert result.returncode == 0
        assert "combo tables missing" in result.stdout
        assert '"execute": false' in result.stdout


def test_combo_lock_and_settle_execute_missing_tables_fail(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    config = tmp_path / "worldcup_combos.yaml"
    config.write_text("enabled: true\ncompetition_key: fifa_world_cup_2026\n", encoding="utf-8")
    env = {
        "PYTHONPATH": str(repo_root / "src"),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'missing_combo_execute_script_tables.db'}",
        "PATH": "/usr/bin:/bin",
    }

    for relative_path in ("scripts/lock_worldcup_combos.py", "scripts/settle_worldcup_combos.py"):
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / relative_path),
                "--config",
                str(config),
                "--execute",
            ],
            cwd=repo_root,
            capture_output=True,
            env=env,
            text=True,
        )
        assert result.returncode != 0
        assert "combo tables missing" in result.stderr


def test_worldcup_odds_sync_execute_requires_refresh_api(repo_root: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts/sync_worldcup_odds_snapshots.py"),
            "--execute",
        ],
        cwd=repo_root,
        capture_output=True,
        env={"PYTHONPATH": str(repo_root / "src"), "PATH": "/usr/bin:/bin"},
        text=True,
    )

    assert result.returncode != 0
    assert "--execute requires --refresh-api" in (result.stdout + result.stderr)


def test_production_docs_reference_existing_commands(repo_root: Path) -> None:
    docs_text = "\n".join(
        [
            (repo_root / "docs/production_runbook.md").read_text(encoding="utf-8"),
            (repo_root / "docs/worldcup_public_rollout.md").read_text(encoding="utf-8"),
        ]
    )

    for expected in (
        "football-predictor worldcup-combos-run",
        "football-predictor worldcup-combos-publish",
        "scripts/lock_worldcup_combos.py",
        "scripts/settle_worldcup_combos.py",
        "scripts/worldcup_coverage_report.py",
        "config/prod_worldcup.example.crontab",
    ):
        assert expected in docs_text
