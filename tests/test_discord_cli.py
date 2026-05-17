from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
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
