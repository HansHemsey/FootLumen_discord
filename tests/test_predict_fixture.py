from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from test_feature_builder import _seed_point_in_time_sources
from test_player_xi_features import PREDICTION_TIME, _seed_base

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.prediction.predict_fixture import predict_fixture
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference


class FakeModel:
    model_version = "mock-model-v1"

    def predict_proba(self, _frame: Any) -> list[list[float]]:
        return [[0.15, 0.20, 0.65]]


class FakeV2Model:
    model_version = "mock-model-v2"
    is_v2_composite = True

    def predict_proba(self, _frame: Any) -> list[list[float]]:
        return [[0.20, 0.25, 0.55]]

    def predict_expert_probabilities(self, _frame: Any) -> list[dict[str, list[float]]]:
        return [
            {
                "poisson_v2": [0.30, 0.30, 0.40],
                "elo_v2": [0.25, 0.25, 0.50],
                "tabular_v2": [0.20, 0.25, 0.55],
            }
        ]


class ExplodingApiClient:
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        raise AssertionError(f"Unexpected live API call endpoint={endpoint} params={params}")


def test_predict_fixture_with_mock_model_persists_prediction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"synthetic model placeholder")
    monkeypatch.setattr(
        "football_predictor.prediction.service.joblib.load",
        lambda _path: FakeModel(),
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'predict_fixture_model.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = predict_fixture(
            -900,
            PREDICTION_TIME,
            model_path,
            refresh_data=False,
            session=session,
            reference=_empty_reference(),
            players_reference=_empty_players_reference(),
            api_client=ExplodingApiClient(),
        )
        prediction_count = session.scalar(select(func.count()).select_from(models.ModelPrediction))

    assert output.sport_source == "model"
    assert output.sport_probabilities is not None
    assert output.sport_probabilities.p_away == pytest.approx(0.65)
    assert output.model_version == "mock-model-v1"
    assert prediction_count == 1


def test_predict_fixture_with_v2_model_persists_expert_probabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"synthetic model placeholder")
    monkeypatch.setattr(
        "football_predictor.prediction.service.joblib.load",
        lambda _path: FakeV2Model(),
    )
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'predict_fixture_v2.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = predict_fixture(
            -900,
            PREDICTION_TIME,
            model_path,
            refresh_data=False,
            session=session,
            reference=_empty_reference(),
            players_reference=_empty_players_reference(),
        )
        record = session.get(models.ModelPrediction, output.model_prediction_id)

    assert output.sport_source == "model_v2"
    assert output.model_version == "mock-model-v2"
    assert output.expert_probabilities["poisson_v2"].p_away == pytest.approx(0.40)
    assert record is not None
    assert "poisson_v2" in record.payload_json["expert_probabilities"]


def test_predict_fixture_fallback_without_model_and_missing_sources(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'predict_fixture_fallback.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        output = predict_fixture(
            -900,
            PREDICTION_TIME,
            tmp_path / "missing-model",
            refresh_data=False,
            session=session,
            reference=_empty_reference(),
            players_reference=_empty_players_reference(),
        )

    assert output.sport_source == "poisson"
    assert output.market_probabilities is None
    assert output.api_probabilities is None
    assert output.explanations
    assert abs(sum(output.probabilities.to_vector()) - 1.0) < 1e-9


def test_predict_fixture_ignores_post_prediction_time_sources(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'predict_fixture_cutoff.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        output = predict_fixture(
            -900,
            PREDICTION_TIME,
            refresh_data=False,
            session=session,
            reference=_empty_reference(),
            players_reference=_empty_players_reference(),
        )

    assert output.market_probabilities is not None
    assert output.market_probabilities.p_home < 0.8
    assert output.api_probabilities is not None
    assert output.api_probabilities.p_home == pytest.approx(0.45)


def _empty_reference() -> ApiFootballReference:
    return ApiFootballReference({"competitions": [], "references": {}})


def _empty_players_reference() -> PlayersReference:
    return PlayersReference({"competitions": []})
