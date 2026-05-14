from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.service import PredictionOutput
from football_predictor.utils.time import utc_now


def test_discord_check_config_cli() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["discord-check-config"])

    assert result.exit_code == 0
    assert "Discord config OK" in result.stdout
    assert "competitions=6" in result.stdout


def test_discord_test_route_cli_dry_run(tmp_path: Path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["discord-test-route", "--competition-key", "ligue1"],
        env={"DATABASE_URL": f"sqlite:///{tmp_path / 'discord_cli.db'}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "status=dry_run" in result.stdout
    assert "https://" not in result.stdout


def test_predict_and_send_cli_dry_run_without_network(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    class FakePredictionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def predict_fixture(self, *args, **kwargs) -> PredictionOutput:
            now = utc_now()
            return PredictionOutput(
                fixture_id=-1,
                match_label="Synthetic Home vs Synthetic Away",
                competition="Synthetic Competition",
                match_date=now,
                prediction_time=now,
                probabilities=ProbabilityTriple(0.5, 0.3, 0.2),
                predicted_result="HOME",
                confidence_label="Medium",
                confidence_score=55.0,
                explanations=["Synthetic explanation"],
                data_quality=DataQuality(),
                data_quality_json={"overall_data_quality_score": 50},
            )

    monkeypatch.setattr("football_predictor.cli.PredictionService", FakePredictionService)

    result = runner.invoke(
        app,
        [
            "predict-and-send",
            "--fixture",
            "-1",
            "--competition-key",
            "ligue1",
            "--dry-run",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'predict_send.db'}",
            "DISCORD_WEBHOOK_URL": "",
            "DISCORD_WEBHOOKS_CONFIG_PATH": str(tmp_path / "missing_webhooks.yaml"),
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "status=dry_run" in result.stdout
    assert "webhook_hash=none" in result.stdout


def test_predict_and_send_cli_live_skips_non_publishable_without_network(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings.cache_clear()
    runner = CliRunner()

    class FakePredictionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def predict_fixture(self, *args, **kwargs) -> PredictionOutput:
            now = utc_now()
            return PredictionOutput(
                fixture_id=-1,
                match_label="Synthetic Home vs Synthetic Away",
                competition="Synthetic Competition",
                match_date=now,
                prediction_time=now,
                probabilities=ProbabilityTriple(0.5, 0.3, 0.2),
                predicted_result="HOME",
                confidence_label="Medium",
                confidence_score=55.0,
                explanations=["Synthetic explanation"],
                data_quality=DataQuality(),
                data_quality_json={"overall_data_quality_score": 90},
            )

    monkeypatch.setattr("football_predictor.cli.PredictionService", FakePredictionService)

    result = runner.invoke(
        app,
        [
            "predict-and-send",
            "--fixture",
            "-1",
            "--competition-key",
            "ligue1",
            "--discord-webhooks",
            "config/discord_webhooks.example.yaml",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{tmp_path / 'predict_send_blocked.db'}",
            "DISCORD_WEBHOOK_URL": "https://example.invalid/blocked",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0
    assert "status=confidence_skipped" in result.stdout
    assert "reason=confidence_below_publish_threshold" in result.stdout


def test_discord_send_cli_live_skips_non_publishable_stored_prediction(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "discord_send_blocked.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    now = utc_now()
    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.Team(team_id=-10, name="Synthetic Home", payload_json={}),
                models.Team(team_id=-20, name="Synthetic Away", payload_json={}),
                models.Fixture(
                    fixture_id=-1,
                    date=now,
                    league_id=61,
                    season=2025,
                    status="NS",
                    status_short="NS",
                    home_team_id=-10,
                    away_team_id=-20,
                    home_team="Synthetic Home",
                    away_team="Synthetic Away",
                    payload_json={},
                ),
            ]
        )
        feature = models.FeatureSnapshot(
            fixture_id=-1,
            prediction_time=now,
            feature_version="synthetic",
            features_json={},
            data_quality_json={"overall_data_quality_score": 90},
        )
        session.add(feature)
        session.flush()
        prediction = models.ModelPrediction(
            fixture_id=-1,
            feature_snapshot_id=feature.id,
            prediction_time=now,
            model_version="synthetic",
            p_home=0.5,
            p_draw=0.3,
            p_away=0.2,
            predicted_outcome="HOME",
            predicted_result="HOME",
            confidence=55.0,
            confidence_label="Medium",
            confidence_score=55.0,
            explanation_json=[],
            explanations_json=[],
            data_quality_json={"overall_data_quality_score": 90},
            payload_json={},
        )
        session.add(prediction)
        session.flush()
        prediction_id = prediction.id

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        ["discord-send", "--prediction-id", str(prediction_id)],
        env={
            "DATABASE_URL": f"sqlite:///{db_path}",
            "DISCORD_WEBHOOK_URL": "https://example.invalid/blocked",
            "DISCORD_WEBHOOKS_CONFIG_PATH": "config/discord_webhooks.example.yaml",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    assert "status=confidence_skipped" in result.stdout
    assert "reason=confidence_below_publish_threshold" in result.stdout
    with session_scope(session_factory) as session:
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        stored_prediction = session.get(models.ModelPrediction, prediction_id)
    assert messages == []
    assert stored_prediction is not None
    assert stored_prediction.payload_json["non_publication_reason"] == (
        "confidence_below_publish_threshold"
    )
