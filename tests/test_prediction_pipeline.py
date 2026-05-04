from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from test_feature_builder import _seed_point_in_time_sources
from test_player_xi_features import PREDICTION_TIME, _home_starting_ids, _lineup, _seed_base
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.service import PredictionService
from football_predictor.reference.lookups import ApiFootballReference


class ExplodingApiClient:
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        raise AssertionError(f"Unexpected live API call endpoint={endpoint} params={params}")


class NoopApiClient:
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        return {"endpoint": endpoint, "params": params or {}, "response": []}


def test_predict_fixture_without_refresh_never_calls_api_and_persists(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'prediction.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            PREDICTION_TIME,
            model_dir=tmp_path / "missing-model",
            refresh_data=False,
            api_client=ExplodingApiClient(),
        )
        feature_count = session.scalar(select(func.count()).select_from(models.FeatureSnapshot))
        prediction = session.scalar(select(models.ModelPrediction))

    assert output.fixture_id == -900
    assert output.sport_source == "poisson"
    assert output.market_probabilities is not None
    assert output.api_probabilities is not None
    assert output.sources_used == ["sport", "market", "api"]
    assert output.feature_snapshot_id is not None
    assert output.model_prediction_id is not None
    assert feature_count == 1
    assert prediction is not None
    assert prediction.feature_snapshot_id == output.feature_snapshot_id
    assert abs(sum(output.probabilities.to_vector()) - 1.0) < 1e-9
    assert output.explanations


def test_predict_fixture_handles_missing_optional_sources_with_low_quality(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'prediction_missing.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            PREDICTION_TIME,
            model_dir=tmp_path / "missing-model",
        )

    assert output.market_probabilities is None
    assert output.api_probabilities is None
    assert output.sport_source == "poisson"
    assert output.sources_used == ["sport"]
    assert output.data_quality_json["odds_available_flag"] is False
    assert output.data_quality_json["api_prediction_available_flag"] is False
    assert 0 <= output.data_quality_json["overall_data_quality_score"] <= 100


def test_predict_fixture_ignores_future_market_and_api_snapshots(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'prediction_leakage.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            PREDICTION_TIME,
        )

    assert output.market_probabilities is not None
    assert output.market_probabilities.p_home < 0.8
    assert output.api_probabilities is not None
    assert output.api_probabilities.p_home == pytest.approx(0.45)
    assert output.to_dict()["sources"]["api"]["HOME"] == pytest.approx(0.45)


def test_predict_fixture_accepts_manual_market_override(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'prediction_override.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            PREDICTION_TIME,
            market_probabilities=ProbabilityTriple(0.8, 0.1, 0.1),
        )

    assert output.market_probabilities is not None
    assert output.market_probabilities.p_home == pytest.approx(0.8)
    assert "market" in output.sources_used


def test_predict_cli_json_outputs_valid_payload_without_refresh(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_prediction.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict",
            "--fixture",
            "-900",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--model-dir",
            str(tmp_path / "missing-model"),
            "--no-refresh",
            "--json",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["fixture_id"] == -900
    assert set(payload["probabilities"]) == {"HOME", "DRAW", "AWAY"}
    assert payload["feature_snapshot_id"] is not None
    assert payload["model_prediction_id"] is not None


def test_predict_cli_console_outputs_summary_without_refresh(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_prediction_console.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_base(session)

    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict",
            "--fixture",
            "-900",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--model-dir",
            str(tmp_path / "missing-model"),
            "--no-refresh",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    assert "Prediction Football" in result.stdout
    assert "Synthetic -10 vs Synthetic -20" in result.stdout


def test_refresh_data_requires_explicit_api_client(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'refresh_guard.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        with pytest.raises(Exception, match="requires an API-Football client"):
            PredictionService(_empty_reference(), session).predict_fixture(
                -900,
                PREDICTION_TIME,
                refresh_data=True,
            )


def test_refresh_without_explicit_prediction_time_uses_cutoff_after_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import football_predictor.prediction.service as service_module

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'refresh_cutoff.db'}")
    session_factory = create_session_factory(engine)
    after_refresh = PREDICTION_TIME + timedelta(seconds=1)

    def fake_refresh(
        self: PredictionService,
        fixture_id: int,
        *,
        api_client: Any,
        save_raw: bool,
    ) -> dict[str, Any]:
        del self, api_client, save_raw
        session.add_all(
            [
                _lineup(fixture_id, -10, "4-3-3", _home_starting_ids(), after_refresh),
                _lineup(fixture_id, -20, "4-2-3-1", list(range(-201, -212)), after_refresh),
            ]
        )
        session.flush()
        return {"synthetic_refresh": True}

    monkeypatch.setattr(service_module, "utc_now", lambda: after_refresh)
    monkeypatch.setattr(PredictionService, "_refresh_dynamic_data", fake_refresh)
    with session_scope(session_factory) as session:
        _seed_base(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            prediction_time=None,
            refresh_data=True,
            api_client=NoopApiClient(),
        )

    assert output.prediction_time == after_refresh
    assert output.data_quality_json["target_lineups_available_flag"] is True


def test_refresh_with_explicit_prediction_time_keeps_strict_cutoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'refresh_explicit_cutoff.db'}")
    session_factory = create_session_factory(engine)
    after_cutoff = PREDICTION_TIME + timedelta(seconds=1)

    def fake_refresh(
        self: PredictionService,
        fixture_id: int,
        *,
        api_client: Any,
        save_raw: bool,
    ) -> dict[str, Any]:
        del self, api_client, save_raw
        session.add_all(
            [
                _lineup(fixture_id, -10, "4-3-3", _home_starting_ids(), after_cutoff),
                _lineup(fixture_id, -20, "4-2-3-1", list(range(-201, -212)), after_cutoff),
            ]
        )
        session.flush()
        return {"synthetic_refresh": True}

    monkeypatch.setattr(PredictionService, "_refresh_dynamic_data", fake_refresh)
    with session_scope(session_factory) as session:
        _seed_base(session)
        output = PredictionService(_empty_reference(), session).predict_fixture(
            -900,
            prediction_time=PREDICTION_TIME,
            refresh_data=True,
            api_client=NoopApiClient(),
        )

    assert output.prediction_time == PREDICTION_TIME
    assert output.data_quality_json["target_lineups_available_flag"] is False


def _empty_reference() -> ApiFootballReference:
    return ApiFootballReference({"competitions": [], "references": {}})
