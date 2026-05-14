from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from sqlalchemy import func, select
from test_feature_builder import _seed_point_in_time_sources
from test_player_xi_features import PREDICTION_TIME, _seed_base
from test_prediction_pipeline import ExplodingApiClient, _empty_reference
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.modeling.v3.draw_risk_model import DrawRiskModel
from football_predictor.modeling.v3.no_draw_winner_model import NoDrawWinnerModel
from football_predictor.prediction.v3_service import PredictionV3Service
from football_predictor.utils.exceptions import PredictionError


class FixedBinaryEstimator:
    classes_ = np.array([0, 1])

    def __init__(self, positive_probability: float) -> None:
        self.positive_probability = positive_probability

    def predict_proba(self, frame: Any) -> np.ndarray:
        rows = len(frame)
        positive = np.full(rows, self.positive_probability)
        return np.column_stack([1.0 - positive, positive])


def test_predict_v3_synthetic_fixture_persists_v3_rows_without_api(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_prediction.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = PredictionV3Service(_empty_reference(), session).predict_fixture_v3(
            -900,
            PREDICTION_TIME,
            model_dir=model_dir,
            refresh_data=False,
            api_client=ExplodingApiClient(),
        )
        feature_count = session.scalar(select(func.count()).select_from(models.FeatureSnapshot))
        v3_feature = session.scalar(select(models.V3FeatureSnapshot))
        v3_prediction = session.scalar(select(models.V3ModelPrediction))
        v2_prediction_count = session.scalar(
            select(func.count()).select_from(models.ModelPrediction)
        )

    assert output.fixture_id == -900
    assert output.v3_feature_snapshot_id is not None
    assert output.v3_model_prediction_id is not None
    assert output.market_probabilities is not None
    assert output.api_probabilities is not None
    assert output.v2_probabilities is not None
    assert output.v2_probabilities.p_home == pytest.approx(1 / 3)
    assert sum(output.probabilities.to_vector()) == pytest.approx(1.0)
    assert output.fusion_strategy == "deterministic_fallback"
    assert feature_count == 1
    assert v2_prediction_count == 0
    assert v3_feature is not None
    assert v3_feature.feature_version == "v3.0"
    assert v3_prediction is not None
    assert v3_prediction.v3_feature_snapshot_id == v3_feature.id
    assert v3_prediction.payload_json["model_family"] == "v3"
    assert v3_prediction.p_market_home is not None
    assert v3_prediction.p_api_home == pytest.approx(0.45)


def test_predict_v3_missing_v2_model_uses_uniform_prior(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_no_v2.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")

    with session_scope(session_factory) as session:
        _seed_base(session)
        output = PredictionV3Service(_empty_reference(), session).predict_fixture_v3(
            -900,
            PREDICTION_TIME,
            model_dir=model_dir,
            v2_model_dir=tmp_path / "missing-v2",
        )

    assert output.v2_probabilities is not None
    assert output.v2_probabilities.to_vector() == pytest.approx([1 / 3, 1 / 3, 1 / 3])
    assert output.v3_model_prediction_id is not None


def test_predict_v3_missing_artifacts_raise_clear_error(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_missing_model.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        with pytest.raises(PredictionError, match="V3 model artifacts not found"):
            PredictionV3Service(_empty_reference(), session).predict_fixture_v3(
                -900,
                PREDICTION_TIME,
                model_dir=tmp_path / "missing-v3",
            )


def test_predict_v3_ignores_future_market_and_api_snapshots(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_leakage.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = PredictionV3Service(_empty_reference(), session).predict_fixture_v3(
            -900,
            PREDICTION_TIME,
            model_dir=model_dir,
        )

    assert output.market_probabilities is not None
    assert output.market_probabilities.p_home < 0.8
    assert output.api_probabilities is not None
    assert output.api_probabilities.p_home == pytest.approx(0.45)


def test_predict_v3_cli_json_outputs_valid_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_v3.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")
    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict-v3",
            "--fixture",
            "-900",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--model-dir",
            str(model_dir),
            "--no-refresh",
            "--json",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["fixture_id"] == -900
    assert payload["v3_model_prediction_id"] is not None
    assert set(payload["probabilities"]) == {"HOME", "DRAW", "AWAY"}
    assert payload["components"]["v2"]["HOME"] == pytest.approx(1 / 3)


def test_predict_v3_cli_discord_dry_run_persists_v3_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_v3_discord.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")
    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict-v3",
            "--fixture",
            "-900",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--model-dir",
            str(model_dir),
            "--no-refresh",
            "--send-discord",
            "--dry-run",
            "--json",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["discord"]["status"] == "dry_run"
    with session_scope(session_factory) as session:
        message = session.scalar(select(models.DiscordMessage))
    assert message is not None
    assert message.model_prediction_id is None
    assert message.payload_json["model_family"] == "v3"
    assert message.payload_json["v3_model_prediction_id"] == payload["v3_model_prediction_id"]
    assert message.payload_json["publication_decision"]["allowed"] is False
    assert message.payload_json["non_publication_reason"] == (
        "confidence_below_publish_threshold"
    )


def test_predict_v3_cli_live_discord_skips_non_publishable_prediction(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_v3_blocked.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    model_dir = _write_synthetic_v3_model(tmp_path / "v3-model")
    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict-v3",
            "--fixture",
            "-900",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--model-dir",
            str(model_dir),
            "--no-refresh",
            "--send-discord",
            "--discord-webhooks",
            "config/discord_webhooks.example.yaml",
            "--json",
        ],
        env={
            "DATABASE_URL": f"sqlite:///{db_path}",
            "DISCORD_WEBHOOK_URL": "https://example.invalid/v3-blocked",
            "PUBLICATION_MIN_DATA_QUALITY_SCORE": "100",
        },
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["discord"]["status"] == "confidence_skipped"
    assert payload["discord"]["reason"] == "confidence_below_publish_threshold"
    with session_scope(session_factory) as session:
        message_count = session.scalar(select(func.count()).select_from(models.DiscordMessage))
        prediction = session.get(models.V3ModelPrediction, payload["v3_model_prediction_id"])
    assert message_count == 0
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == payload["discord"]["reason"]


def _write_synthetic_v3_model(path: Path) -> Path:
    draw = DrawRiskModel(
        model_version="v3.0-draw-risk-test",
        feature_names=["draw_risk_score"],
        estimator=FixedBinaryEstimator(0.28),
        feature_coverage={"draw_risk_score": 1.0},
        calibration_decision={"method": None, "reason": "synthetic"},
        estimator_name="fixed_binary",
    )
    no_draw = NoDrawWinnerModel(
        model_version="v3.0-no-draw-winner-test",
        feature_names=["ndw_home_away_strength_edge"],
        estimator=FixedBinaryEstimator(0.62),
        feature_coverage={"ndw_home_away_strength_edge": 1.0},
        calibration_decision={"method": None, "reason": "synthetic"},
        estimator_name="fixed_binary",
    )
    draw.save(path / "draw_risk" / "model.joblib")
    no_draw.save(path / "no_draw_winner" / "model.joblib")
    return path
