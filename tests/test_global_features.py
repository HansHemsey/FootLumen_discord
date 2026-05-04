from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from test_player_xi_features import PREDICTION_TIME, _seed_base

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.global_features import build_feature_snapshot


def test_global_feature_snapshot_merges_sources_and_is_idempotent(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'global_features.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_market_and_api_sources(session)
        first = build_feature_snapshot(session, -900, PREDICTION_TIME)
        second = build_feature_snapshot(session, -900, PREDICTION_TIME)
        count = session.scalar(select(func.count()).select_from(models.FeatureSnapshot))

    features = first.features_json
    quality = first.data_quality_json

    assert first.id == second.id
    assert count == 1
    assert first.feature_version == "global_features_v1"
    assert features["feature_version"] == "global_features_v1"
    assert features["p_market_home"] is not None
    assert features["market_bookmaker_count"] == 1
    assert features["p_api_home"] == 0.45
    assert features["api_prediction_winner_team_id"] == -10
    assert "target" not in features
    assert "home_goals" not in features
    assert -199 not in {row["player_id"] for row in features["home_team_expected_xi_json"]}
    assert quality["odds_available"] is True
    assert quality["api_prediction_available"] is True
    assert quality["data_quality_score"] > 0


def test_global_feature_snapshot_ignores_future_market_and_api_snapshots(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'global_leakage.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_market_and_api_sources(session)
        snapshot = build_feature_snapshot(session, -900, PREDICTION_TIME)

    features = snapshot.features_json
    assert features["p_market_home"] < 0.9
    assert features["p_api_home"] == 0.45
    assert features["api_prediction_fetched_at"] == "2026-05-02T09:00:00"


def test_global_feature_snapshot_tolerates_missing_optional_sources(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'global_missing.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        snapshot = build_feature_snapshot(session, -900, PREDICTION_TIME)

    assert snapshot.features_json["p_market_home"] is None
    assert snapshot.features_json["p_api_home"] is None
    assert snapshot.data_quality_json["odds_available"] is False
    assert snapshot.data_quality_json["api_prediction_available"] is False


def _seed_market_and_api_sources(session) -> None:
    session.add_all(
        [
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-1,
                bookmaker_name="Synthetic Book",
                bet_id=-1,
                bet_name="Match Winner",
                odd_home=2.0,
                odd_draw=3.5,
                odd_away=4.0,
                values_json=[],
                fetched_at=datetime(2026, 5, 2, 9, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-1,
                bookmaker_name="Synthetic Book",
                bet_id=-1,
                bet_name="Match Winner",
                odd_home=1.01,
                odd_draw=20.0,
                odd_away=30.0,
                values_json=[],
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.ApiPredictionSnapshot(
                fixture_id=-900,
                winner_team_id=-10,
                percent_home=45,
                percent_draw=30,
                percent_away=25,
                advice="Synthetic before cutoff",
                fetched_at=datetime(2026, 5, 2, 9, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.ApiPredictionSnapshot(
                fixture_id=-900,
                winner_team_id=-20,
                percent_home=99,
                percent_draw=0,
                percent_away=1,
                advice="Synthetic future leak",
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
        ]
    )
