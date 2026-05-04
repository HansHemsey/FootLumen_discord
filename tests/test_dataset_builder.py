from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from test_player_features import _fixture, _seed_team_history

from football_predictor.backtesting.dataset_builder import (
    build_training_dataset,
    create_time_based_split,
)
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope


def test_dataset_builder_targets_and_feature_snapshots(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dataset_builder.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        _seed_extra_results(session)
        frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset_hours=24,
        )
        snapshots = session.query(models.FeatureSnapshot).all()

    assert {"HOME", "DRAW", "AWAY"} <= set(frame["target"])
    assert "feature_snapshot_id" in frame.columns
    assert "fixture_date" in frame.columns
    assert "prediction_time" in frame.columns
    assert -1000 not in set(frame["fixture_id"])
    assert all("target" not in snapshot.features_json for snapshot in snapshots)
    assert all("home_goals" not in snapshot.features_json for snapshot in snapshots)
    assert all("away_goals" not in snapshot.features_json for snapshot in snapshots)


def test_dataset_builder_saves_csv_and_parquet(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dataset_builder_export.db'}")
    session_factory = create_session_factory(engine)
    csv_path = tmp_path / "dataset.csv"
    parquet_path = tmp_path / "dataset.parquet"

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        csv_frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            save_path=csv_path,
        )
        parquet_frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            save_path=parquet_path,
        )

    assert len(pd.read_csv(csv_path)) == len(csv_frame)
    assert len(pd.read_parquet(parquet_path)) == len(parquet_frame)


def test_create_time_based_split_preserves_chronological_order() -> None:
    frame = pd.DataFrame(
        [
            {"fixture_id": 1, "fixture_date": "2026-01-01T12:00:00+00:00"},
            {"fixture_id": 2, "fixture_date": "2026-02-01T12:00:00+00:00"},
            {"fixture_id": 3, "fixture_date": "2026-03-01T12:00:00+00:00"},
            {"fixture_id": 4, "fixture_date": "2026-04-01T12:00:00+00:00"},
        ]
    )

    train, valid, test = create_time_based_split(
        frame,
        train_until=datetime(2026, 2, 1, 12, tzinfo=UTC),
        valid_until=datetime(2026, 3, 1, 12, tzinfo=UTC),
    )

    assert list(train["fixture_id"]) == [1, 2]
    assert list(valid["fixture_id"]) == [3]
    assert list(test["fixture_id"]) == [4]


def _seed_extra_results(session) -> None:
    _fixture(
        session,
        -1010,
        datetime(2026, 4, 10, 19, tzinfo=UTC),
        -10,
        -20,
        1,
        1,
    )
    _fixture(
        session,
        -1011,
        datetime(2026, 4, 12, 19, tzinfo=UTC),
        -10,
        -20,
        0,
        2,
    )
