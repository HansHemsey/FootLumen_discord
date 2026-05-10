from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from football_predictor.backtesting.v3_dataset_builder import (
    DRAW_TARGET_COL,
    NDW_TARGET_COL,
    OUTCOME_COL,
    add_chronological_split_column,
    build_v3_draw_risk_dataset,
    build_v3_no_draw_winner_dataset,
    build_v3_stacker_dataset,
    chronological_splits,
)
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope


def test_build_v3_draw_risk_dataset_targets_and_m30_prediction_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_draw_dataset.db'}")
    factory = create_session_factory(engine)
    kickoff = datetime(2026, 5, 1, 20, 0, tzinfo=UTC)

    with session_scope(factory) as session:
        _seed_v3_dataset_fixtures(session, kickoff)

    with session_scope(factory) as session:
        frame = build_v3_draw_risk_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
        )

    assert list(frame["fixture_id"]) == [-1000, -1001, -1002]
    assert list(frame[OUTCOME_COL]) == ["DRAW", "HOME", "AWAY"]
    assert list(frame[DRAW_TARGET_COL]) == [1, 0, 0]
    assert frame.iloc[0]["prediction_time"] == (kickoff - timedelta(minutes=30)).isoformat()
    assert set(frame["feature_version"]) == {"v3.0"}
    assert "draw_risk_score" in frame.columns
    assert "ndw_home_away_strength_edge" in frame.columns
    assert "official_lineup_available_flag" in frame.columns


def test_build_v3_no_draw_winner_dataset_filters_draws_and_targets_home_wins(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'v3_ndw_dataset.db'}")
    factory = create_session_factory(engine)
    kickoff = datetime(2026, 5, 1, 20, 0, tzinfo=UTC)

    with session_scope(factory) as session:
        _seed_v3_dataset_fixtures(session, kickoff)

    with session_scope(factory) as session:
        frame = build_v3_no_draw_winner_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
        )

    assert list(frame["fixture_id"]) == [-1001, -1002]
    assert list(frame[OUTCOME_COL]) == ["HOME", "AWAY"]
    assert list(frame[NDW_TARGET_COL]) == [1, 0]
    assert frame[DRAW_TARGET_COL].sum() == 0


def test_chronological_splits_and_split_column_are_ordered() -> None:
    frame = pd.DataFrame(
        {
            "fixture_id": [5, 1, 4, 2, 3],
            "fixture_date": [
                "2026-05-05T20:00:00+00:00",
                "2026-05-01T20:00:00+00:00",
                "2026-05-04T20:00:00+00:00",
                "2026-05-02T20:00:00+00:00",
                "2026-05-03T20:00:00+00:00",
            ],
        }
    )

    splits = chronological_splits(frame)
    assert list(splits.train["fixture_id"]) == [1, 2, 3]
    assert list(splits.valid["fixture_id"]) == [4]
    assert list(splits.test["fixture_id"]) == [5]

    labeled = add_chronological_split_column(frame)
    assert list(labeled["fixture_id"]) == [1, 2, 3, 4, 5]
    assert list(labeled["split"]) == ["train", "train", "train", "valid", "test"]


def test_build_v3_stacker_dataset_joins_validation_predictions() -> None:
    base = pd.DataFrame(
        {
            "fixture_id": [-1000, -1001, -1002],
            "fixture_date": [
                "2026-05-01T20:00:00+00:00",
                "2026-05-02T20:00:00+00:00",
                "2026-05-03T20:00:00+00:00",
            ],
            "prediction_time": [
                "2026-05-01T19:30:00+00:00",
                "2026-05-02T19:30:00+00:00",
                "2026-05-03T19:30:00+00:00",
            ],
            "target": ["DRAW", "HOME", "AWAY"],
            "split": ["train", "valid", "valid"],
            "market_home": [0.34, 0.50, 0.28],
            "market_draw": [0.32, 0.25, 0.30],
            "market_away": [0.34, 0.25, 0.42],
            "api_pred_home": [0.33, 0.48, 0.30],
            "api_pred_draw": [0.34, 0.26, 0.28],
            "api_pred_away": [0.33, 0.26, 0.42],
            "data_quality_score": [70, 80, 75],
            "official_lineup_available_flag": [0, 1, 0],
        }
    )
    draw_preds = pd.DataFrame(
        {
            "fixture_id": [-1001, -1002],
            "p_v3_draw_risk": [0.24, 0.31],
        }
    )
    ndw_preds = pd.DataFrame(
        {
            "fixture_id": [-1001, -1002],
            "p_v3_home_no_draw": [0.66, 0.40],
        }
    )
    v2_preds = pd.DataFrame(
        {
            "fixture_id": [-1001, -1002],
            "p_v2_home": [0.52, 0.29],
            "p_v2_draw": [0.26, 0.30],
            "p_v2_away": [0.22, 0.41],
        }
    )

    frame = build_v3_stacker_dataset(
        base,
        draw_preds,
        ndw_preds,
        v2_predictions=v2_preds,
        split_name="valid",
    )

    assert list(frame["fixture_id"]) == [-1001, -1002]
    assert list(frame[OUTCOME_COL]) == ["HOME", "AWAY"]
    assert list(frame["p_v3_away_no_draw"]) == pytest.approx([0.34, 0.60])
    assert list(frame["p_market_home_no_draw"]) == pytest.approx(
        [0.50 / (0.50 + 0.25), 0.28 / (0.28 + 0.42)]
    )
    assert frame["p_v2_home"].isna().sum() == 0
    assert frame["data_quality_score"].tolist() == [80, 75]


def test_build_v3_stacker_dataset_rejects_missing_predictions() -> None:
    base = pd.DataFrame(
        {
            "fixture_id": [-1000],
            "fixture_date": ["2026-05-01T20:00:00+00:00"],
            "prediction_time": ["2026-05-01T19:30:00+00:00"],
            "target": ["HOME"],
            "split": ["valid"],
        }
    )
    draw_preds = pd.DataFrame({"fixture_id": [-999], "p_v3_draw_risk": [0.20]})
    ndw_preds = pd.DataFrame({"fixture_id": [-1000], "p_v3_home_no_draw": [0.60]})

    with pytest.raises(ValueError, match="draw_risk_predictions"):
        build_v3_stacker_dataset(base, draw_preds, ndw_preds)


def _seed_v3_dataset_fixtures(session, kickoff: datetime) -> None:
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={}),
            models.Team(team_id=-30, name="Synthetic Opp 1", payload_json={}),
            models.Team(team_id=-40, name="Synthetic Opp 2", payload_json={}),
        ]
    )
    fixtures = [
        (-1000, kickoff, -10, -20, 1, 1),
        (-1001, kickoff + timedelta(days=1), -10, -30, 2, 0),
        (-1002, kickoff + timedelta(days=2), -40, -20, 0, 1),
        (-9001, kickoff - timedelta(days=10), -10, -40, 1, 0),
        (-9002, kickoff - timedelta(days=10), -30, -20, 0, 0),
    ]
    for fixture_id, date, home, away, home_goals, away_goals in fixtures:
        league_id = -100 if fixture_id > -2000 else -99
        session.add(
            models.Fixture(
                fixture_id=fixture_id,
                date=date,
                league_id=league_id,
                season=2026,
                status_short="FT",
                status_long="Full Time",
                home_team_id=home,
                away_team_id=away,
                home_team=f"Team {home}",
                away_team=f"Team {away}",
                home_goals=home_goals,
                away_goals=away_goals,
                payload_json={"synthetic": True},
            )
        )
