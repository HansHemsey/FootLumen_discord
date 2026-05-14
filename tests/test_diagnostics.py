from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballClient
from football_predictor.api.exceptions import ApiFootballServerError
from football_predictor.cli import app
from football_predictor.config.settings import Settings, get_settings
from football_predictor.db import models
from football_predictor.db.session import create_db_engine, create_session_factory, init_db
from football_predictor.utils.diagnostics import (
    DiagnosticStatus,
    build_data_quality_report,
    build_diagnostic_report,
)
from football_predictor.utils.logging import get_logger, log_event


def test_diagnostic_report_checks_reference_files(repo_root: Path) -> None:
    settings = Settings(
        _env_file=None,
        **{
            "DATABASE_URL": "sqlite:///:memory:",
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
            "COMPETITIONS_CONFIG_PATH": str(repo_root / "config/competitions.example.yaml"),
        },
    )

    report = build_diagnostic_report(settings, version="test")
    checks = {check.name: check for check in report.checks}

    assert checks["api_football_reference"].status == DiagnosticStatus.OK
    assert checks["api_football_reference_md"].status == DiagnosticStatus.OK
    assert checks["api_football_players_reference"].status == DiagnosticStatus.OK
    assert checks["api_football_players_reference_md"].status == DiagnosticStatus.OK
    assert checks["api_football_players_cache"].status == DiagnosticStatus.OK
    assert checks["api_football_players_cache"].details["business_source"] is False
    assert checks["model_dir"].status == DiagnosticStatus.OK
    assert checks["api_football_reference"].details["counts"]["leagues"] > 0


def test_diagnostic_report_checks_database_tables(tmp_path: Path, repo_root: Path) -> None:
    database_path = tmp_path / "doctor.db"
    engine = create_db_engine(f"sqlite:///{database_path}")
    init_db(engine)
    settings = Settings(
        _env_file=None,
        **{
            "DATABASE_URL": f"sqlite:///{database_path}",
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
            "COMPETITIONS_CONFIG_PATH": str(repo_root / "config/competitions.example.yaml"),
        },
    )

    report = build_diagnostic_report(settings, version="test")
    database_check = {check.name: check for check in report.checks}["database"]

    assert database_check.status == DiagnosticStatus.OK
    assert database_check.details["missing_tables"] == []


def test_diagnostic_report_invalid_json_is_error(tmp_path: Path) -> None:
    bad_reference = tmp_path / "bad_reference.json"
    bad_reference.write_text("{not-json", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        **{
            "DATABASE_URL": "sqlite:///:memory:",
            "API_FOOTBALL_REFERENCE_PATH": str(bad_reference),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(bad_reference),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(bad_reference),
        },
    )

    report = build_diagnostic_report(settings, version="test", check_db=False)

    assert report.has_critical_errors
    assert any(check.status == DiagnosticStatus.ERROR for check in report.checks)


def test_doctor_json_and_strict_exit_on_missing_reference(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["doctor", "--json", "--strict"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'diagnostics.db'}",
            "API_FOOTBALL_REFERENCE_PATH": str(tmp_path / "missing_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
        },
    )
    get_settings.cache_clear()

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["has_critical_errors"] is True
    assert "missing_reference" in result.stdout


def test_doctor_masks_configured_secrets_in_json(tmp_path: Path, repo_root: Path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()
    synthetic_key = "synthetic-api-key-value"
    synthetic_webhook = "https://discord.com/api/webhooks/synthetic/id"

    result = runner.invoke(
        app,
        ["doctor", "--json"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'diagnostics.db'}",
            "API_FOOTBALL_KEY": synthetic_key,
            "DISCORD_WEBHOOK_URL": synthetic_webhook,
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert synthetic_key not in result.stdout
    assert synthetic_webhook not in result.stdout
    assert "hash=" in result.stdout
    json.loads(result.stdout)


def test_data_quality_report_counts_local_snapshots(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'quality.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    fetched_at = datetime(2026, 5, 2, 8, tzinfo=UTC)
    with session_factory() as session:
        session.add_all(
            [
                models.Team(team_id=-101, name="Synthetic Home"),
                models.Team(team_id=-102, name="Synthetic Away"),
                models.Fixture(
                    fixture_id=-2001,
                    league_id=-10,
                    season=2099,
                    date=datetime(2026, 4, 20, 15, tzinfo=UTC),
                    status_short="FT",
                    home_team_id=-101,
                    away_team_id=-102,
                    home_team="Synthetic Home",
                    away_team="Synthetic Away",
                    home_goals=2,
                    away_goals=1,
                ),
                models.Fixture(
                    fixture_id=-1001,
                    league_id=-10,
                    season=2099,
                    date=datetime(2026, 5, 2, 15, tzinfo=UTC),
                    status_short="NS",
                    home_team_id=-101,
                    away_team_id=-102,
                    home_team="Synthetic Home",
                    away_team="Synthetic Away",
                ),
                models.OddsSnapshot(
                    fixture_id=-1001,
                    league_id=-10,
                    season=2099,
                    bookmaker_id=None,
                    bet_id=None,
                    fetched_at=fetched_at,
                    values_json=[],
                ),
                models.StandingSnapshot(
                    league_id=-10,
                    season=2099,
                    team_id=-101,
                    snapshot_date=fetched_at,
                    fetched_at=fetched_at,
                ),
                models.FixtureStatistics(
                    fixture_id=-1001,
                    team_id=-101,
                    fetched_at=fetched_at,
                    statistics_json={"Total Shots": 10},
                ),
                models.Injury(
                    fixture_id=-1001,
                    team_id=-101,
                    player_id=None,
                    fetched_at=fetched_at,
                ),
                models.FixtureLineup(
                    fixture_id=-1001,
                    team_id=-101,
                    formation="4-3-3",
                    fetched_at=fetched_at,
                ),
                models.FixturePlayerStats(
                    fixture_id=-1001,
                    team_id=-101,
                    player_id=-201,
                    fetched_at=fetched_at,
                ),
                models.ApiPredictionSnapshot(fixture_id=-1001, fetched_at=fetched_at),
                models.FeatureSnapshot(
                    fixture_id=-1001,
                    prediction_time=fetched_at,
                    feature_version="diagnostics_test",
                    features_json={},
                    data_quality_json={
                        "data_quality_version": "dq_v2",
                        "overall_data_quality_score": 72,
                        "publication_data_quality_score": 72,
                        "publication_blockers": [],
                        "source_quality_json": {
                            "odds_1x2": {
                                "available": True,
                                "checked": True,
                                "fresh": True,
                                "latest_fetched_at": fetched_at.isoformat(),
                                "age_minutes": 0,
                                "age_hours": 0,
                                "count": 1,
                                "score": 20,
                                "warnings": [],
                            }
                        },
                    },
                ),
            ]
        )
        session.commit()

        report = build_data_quality_report(session, fixture_id=-1001)

    assert report["fixtures_total"] == 1
    assert report["fixtures_future"] == 1
    assert report["historical_home_count"] == 1
    assert report["historical_away_count"] == 1
    assert report["historical_home_available"] is True
    assert report["historical_away_available"] is True
    assert report["fixture_statistics"] == 1
    assert report["odds_snapshots"] == 1
    assert report["lineups"] == 1
    assert report["injuries"] == 1
    assert report["player_stats"] == 1
    assert report["api_predictions"] == 1
    assert report["availability"]["match_statistics_available"] is True
    assert report["availability"]["reference_docs_available"] is True
    assert report["overall_data_quality_score"] == 72
    assert report["average_overall_data_quality_score"] == 72
    assert report["source_freshness"]["odds_1x2"]["fresh_count"] == 1
    assert report["publication_readiness"]["ready_count"] == 1
    assert report["fixtures_ready"] == 1
    assert report["fixtures_blocked"] == 0


def test_data_quality_cli_rejects_unknown_positive_league(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["data-quality", "--league", "999999", "--season", "2099"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'quality.db'}",
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 2
    assert "Unknown league_id" in result.output


def test_data_quality_cli_json_empty_db(tmp_path: Path, repo_root: Path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["data-quality", "--json"],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["fixtures_total"] == 0
    assert payload["odds_snapshots"] == 0


def test_data_quality_cli_week_markdown_and_json_outputs(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    db_path = tmp_path / "quality_outputs.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    kickoff = datetime(2026, 5, 6, 15, tzinfo=UTC)
    with session_factory() as session:
        session.add_all(
            [
                models.Team(team_id=-101, name="Synthetic Home"),
                models.Team(team_id=-102, name="Synthetic Away"),
                models.Fixture(
                    fixture_id=-3001,
                    league_id=-10,
                    season=2099,
                    date=kickoff,
                    status_short="NS",
                    home_team_id=-101,
                    away_team_id=-102,
                    home_team="Synthetic Home",
                    away_team="Synthetic Away",
                ),
                models.FeatureSnapshot(
                    fixture_id=-3001,
                    prediction_time=kickoff,
                    feature_version="v3.0",
                    features_json={},
                    data_quality_json={
                        "data_quality_version": "dq_v2",
                        "publication_data_quality_score": 85,
                        "publication_blockers": [],
                        "source_quality_json": {
                            "odds_1x2": {
                                "available": True,
                                "checked": True,
                                "fresh": True,
                                "latest_fetched_at": kickoff.isoformat(),
                                "count": 1,
                                "score": 20,
                                "warnings": [],
                            }
                        },
                    },
                ),
                models.FeatureSnapshot(
                    fixture_id=-3001,
                    prediction_time=kickoff,
                    feature_version="v1",
                    features_json={},
                    data_quality_json={
                        "publication_data_quality_score": 10,
                        "publication_blockers": [],
                    },
                ),
            ]
        )
        session.commit()

    get_settings.cache_clear()
    json_path = tmp_path / "quality.json"
    markdown_path = tmp_path / "quality.md"
    result = CliRunner().invoke(
        app,
        [
            "data-quality",
            "--week-of",
            "2026-05-04",
            "--model-family",
            "v3",
            "--json",
            "--json-output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ],
        env={
            "DATABASE_URL": f"sqlite:///{db_path}",
            "API_FOOTBALL_REFERENCE_PATH": str(repo_root / "docs/api_football_reference.json"),
            "API_FOOTBALL_PLAYERS_REFERENCE_PATH": str(
                repo_root / "docs/api_football_players_reference.json"
            ),
            "API_FOOTBALL_PLAYERS_CACHE_PATH": str(
                repo_root / "docs/api_football_players_cache.json"
            ),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["scope"]["week_of"] == "2026-05-04"
    assert payload["scope"]["model_family"] == "v3"
    assert payload["publication_readiness"]["ready_count"] == 1
    assert json.loads(json_path.read_text(encoding="utf-8"))["fixtures_ready"] == 1
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Data Quality Report" in markdown
    assert "odds_1x2" in markdown


def test_log_event_masks_secret_context(caplog) -> None:
    logger = get_logger("diagnostics_test")
    webhook_url = "https://discord.com/api/webhooks/synthetic/id"
    api_key = "synthetic-api-key-value"

    with caplog.at_level(logging.INFO, logger="football_predictor"):
        log_event(
            logger,
            "info",
            "diagnostic_check",
            webhook_url=webhook_url,
            api_key=api_key,
            authorization=f"Bearer {api_key}",
            note=f"webhook={webhook_url}",
        )

    text = caplog.text
    assert "event=diagnostic_check" in text
    assert webhook_url not in text
    assert api_key not in text
    assert "<redacted>" in text


def test_api_server_error_message_is_actionable_without_secret() -> None:
    api_key = "synthetic-api-key-value"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-apisports-key"] == api_key
        return httpx.Response(500, json={"errors": {"server": "synthetic failure"}})

    client = ApiFootballClient(
        api_key=api_key,
        retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ApiFootballServerError) as exc_info:
        client.get("/fixtures", params={"fixture": -1001})

    message = str(exc_info.value)
    assert "endpoint=/fixtures" in message
    assert "status_code=500" in message
    assert "synthetic-api-key-value" not in message
