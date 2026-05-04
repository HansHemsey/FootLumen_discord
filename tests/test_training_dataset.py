from __future__ import annotations

from datetime import timedelta

import pandas as pd
from test_player_features import _seed_team_history
from typer.testing import CliRunner

from football_predictor.backtesting.dataset import (
    build_training_dataset,
    parse_prediction_window,
)
from football_predictor.cli import app
from football_predictor.config import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope


def test_build_training_dataset_encodes_targets_and_excludes_unfinished(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dataset.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset=timedelta(hours=24),
        )
        snapshots = session.query(models.FeatureSnapshot).all()

    assert len(frame) == 3
    assert set(frame["target"]) == {"HOME"}
    assert -1000 not in set(frame["fixture_id"])
    assert "feature_snapshot_id" in frame.columns
    assert "home_goals" in frame.columns
    assert "away_goals" in frame.columns
    assert "data_quality_score" in frame.columns
    assert all("target" not in snapshot.features_json for snapshot in snapshots)
    assert all("home_goals" not in snapshot.features_json for snapshot in snapshots)


def test_build_training_dataset_supports_prediction_windows_and_quality_filter(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dataset_window.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            prediction_offset=parse_prediction_window("6h"),
            min_quality=101,
        )

    assert frame.empty
    assert parse_prediction_window("24h") == timedelta(hours=24)
    assert parse_prediction_window("40m") == timedelta(minutes=40)


def test_training_dataset_exports_csv_and_parquet(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dataset_export.db'}")
    session_factory = create_session_factory(engine)
    csv_path = tmp_path / "training.csv"
    parquet_path = tmp_path / "training.parquet"

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        csv_frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            output_path=csv_path,
            output_format="csv",
            limit=1,
        )
        parquet_frame = build_training_dataset(
            session,
            league_ids=[-100],
            seasons=[2026],
            output_path=parquet_path,
            output_format="parquet",
            limit=1,
        )

    assert csv_path.exists()
    assert parquet_path.exists()
    assert len(pd.read_csv(csv_path)) == len(csv_frame)
    assert len(pd.read_parquet(parquet_path)) == len(parquet_frame)


def test_cli_build_dataset_uses_local_database_without_network(tmp_path) -> None:
    get_settings.cache_clear()
    database_url = f"sqlite:///{tmp_path / 'cli_dataset.db'}"
    engine = create_db_and_tables(database_url)
    session_factory = create_session_factory(engine)
    output_path = tmp_path / "cli_dataset.csv"
    with session_scope(session_factory) as session:
        _seed_team_history(session)

    result = CliRunner().invoke(
        app,
        [
            "build-dataset",
            "--league=-100",
            "--season",
            "2026",
            "--prediction-window",
            "24h",
            "--output",
            str(output_path),
            "--format",
            "csv",
            "--limit",
            "1",
        ],
        env={"DATABASE_URL": database_url},
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert "rows" in result.stdout
    get_settings.cache_clear()
