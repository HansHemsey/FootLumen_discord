from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from alembic import command
from football_predictor.db import models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)


def _has_columns(inspector, table_name: str, expected_columns: set[str]) -> bool:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return expected_columns.issubset(columns)


def _index_names(inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def _foreign_key_targets(inspector, table_name: str) -> set[tuple[tuple[str, ...], str]]:
    return {
        (tuple(fk["constrained_columns"]), fk["referred_table"])
        for fk in inspector.get_foreign_keys(table_name)
    }


def test_init_db_creates_v3_tables_and_columns(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'v3_schema.db'}")

    init_db(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"v3_feature_snapshots", "v3_model_predictions"}.issubset(tables)

    assert _has_columns(
        inspector,
        "v3_feature_snapshots",
        {
            "fixture_id",
            "prediction_time",
            "feature_version",
            "official_lineup_available_flag",
            "features_json",
            "data_quality_json",
            "created_at",
            "updated_at",
        },
    )
    assert _has_columns(
        inspector,
        "v3_model_predictions",
        {
            "fixture_id",
            "v3_feature_snapshot_id",
            "prediction_time",
            "model_version",
            "fusion_strategy",
            "p_v3_final_home",
            "p_v3_final_draw",
            "p_v3_final_away",
            "p_v3_draw_risk",
            "p_v3_home_no_draw",
            "p_v3_away_no_draw",
            "p_v2_home",
            "p_v2_draw",
            "p_v2_away",
            "p_market_home",
            "p_market_draw",
            "p_market_away",
            "p_api_home",
            "p_api_draw",
            "p_api_away",
            "data_quality_score",
            "official_lineup_available_flag",
            "confidence_score",
            "confidence_label",
            "predicted_result",
            "expert_probabilities_json",
            "explanations_json",
            "data_quality_json",
            "payload_json",
        },
    )
    assert {
        "ix_v3_feature_snapshot_fixture_time",
        "ix_v3_feature_snapshots_fixture_id",
        "ix_v3_feature_snapshots_prediction_time",
    }.issubset(_index_names(inspector, "v3_feature_snapshots"))
    assert {
        "ix_v3_prediction_fixture_time",
        "ix_v3_prediction_model_version",
        "ix_v3_model_predictions_fixture_id",
        "ix_v3_model_predictions_prediction_time",
        "ix_v3_model_predictions_v3_feature_snapshot_id",
    }.issubset(_index_names(inspector, "v3_model_predictions"))
    assert {
        (("fixture_id",), "fixtures"),
    }.issubset(_foreign_key_targets(inspector, "v3_feature_snapshots"))
    assert {
        (("fixture_id",), "fixtures"),
        (("v3_feature_snapshot_id",), "v3_feature_snapshots"),
    }.issubset(_foreign_key_targets(inspector, "v3_model_predictions"))
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("v3_feature_snapshots")
    }
    assert "uq_v3_feature_snapshot" in unique_constraints


def test_v3_feature_snapshot_unique_constraint(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'v3_uniq.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 5, 8, 14, 30, tzinfo=UTC)

    with session_scope(session_factory) as session:
        # Synthetic DB-only IDs.
        session.add(models.Venue(venue_id=-1, name="Synthetic Venue"))
        session.add(models.Team(team_id=-10, name="Synthetic Home", payload_json={}))
        session.add(models.Team(team_id=-20, name="Synthetic Away", payload_json={}))
        session.add(
            models.Fixture(
                fixture_id=-100,
                date=now,
                league_id=-30,
                season=2026,
                status_short="NS",
                status_long="Not Started",
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={},
            )
        )
        session.add(
            models.V3FeatureSnapshot(
                fixture_id=-100,
                prediction_time=now,
                feature_version="v3.0",
                official_lineup_available_flag=False,
                features_json={"x": 1},
                data_quality_json={"score": 80},
            )
        )

    with pytest.raises(IntegrityError), session_scope(session_factory) as session:
        session.add(
            models.V3FeatureSnapshot(
                fixture_id=-100,
                prediction_time=now,
                feature_version="v3.0",
                official_lineup_available_flag=True,
                features_json={"x": 2},
                data_quality_json={"score": 90},
            )
        )


def test_v3_model_prediction_insert_and_relationship(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'v3_pred.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 5, 8, 14, 30, tzinfo=UTC)

    with session_scope(session_factory) as session:
        # Synthetic DB-only IDs.
        session.add(models.Venue(venue_id=-1, name="Synthetic Venue"))
        session.add(models.Team(team_id=-10, name="Synthetic Home", payload_json={}))
        session.add(models.Team(team_id=-20, name="Synthetic Away", payload_json={}))
        session.add(
            models.Fixture(
                fixture_id=-100,
                date=now,
                league_id=-30,
                season=2026,
                status_short="NS",
                status_long="Not Started",
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={},
            )
        )
        feature_snapshot = models.V3FeatureSnapshot(
            fixture_id=-100,
            prediction_time=now,
            feature_version="v3.0",
            official_lineup_available_flag=True,
            features_json={"home_team_ppg_last10": 1.8},
            data_quality_json={"score": 82, "has_official_lineup_home": True},
        )
        session.add(feature_snapshot)
        session.flush()

        prediction = models.V3ModelPrediction(
            fixture_id=-100,
            v3_feature_snapshot_id=feature_snapshot.id,
            prediction_time=now,
            model_version="v3.0-final",
            fusion_strategy="stacker_lr",
            p_v3_final_home=0.52,
            p_v3_final_draw=0.27,
            p_v3_final_away=0.21,
            p_v3_draw_risk=0.27,
            p_v3_home_no_draw=0.715,
            p_v3_away_no_draw=0.285,
            p_v2_home=0.49,
            p_v2_draw=0.28,
            p_v2_away=0.23,
            p_market_home=0.50,
            p_market_draw=0.27,
            p_market_away=0.23,
            p_api_home=0.51,
            p_api_draw=0.26,
            p_api_away=0.23,
            data_quality_score=82.0,
            official_lineup_available_flag=True,
            confidence_score=24.0,
            confidence_label="Medium",
            predicted_result="HOME",
            expert_probabilities_json={
                "draw_risk": 0.27,
                "no_draw_winner_home": 0.715,
            },
            explanations_json=[
                {"factor": "home_advantage_edge", "shap": 0.12},
            ],
            data_quality_json={"score": 82},
            payload_json={"component_versions": {"draw_risk": "v3.0", "ndw": "v3.0"}},
        )
        session.add(prediction)

    with session_scope(session_factory) as session:
        result = session.scalar(select(models.V3ModelPrediction))
        snapshot = session.scalar(select(models.V3FeatureSnapshot))

    assert result is not None
    assert result.fusion_strategy == "stacker_lr"
    assert result.predicted_result == "HOME"
    assert result.p_v3_final_home == pytest.approx(0.52)
    assert result.p_v3_draw_risk == pytest.approx(0.27)
    assert snapshot is not None
    assert result.v3_feature_snapshot_id == snapshot.id
    assert snapshot.official_lineup_available_flag is True


def test_alembic_upgrade_head_creates_v3_tables(tmp_path: Path, repo_root: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'alembic_v3.db'}"
    alembic_cfg = Config(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_cfg, "head")

    engine = create_db_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {"v3_feature_snapshots", "v3_model_predictions"}.issubset(tables)
    indexes_pred = {idx["name"] for idx in inspector.get_indexes("v3_model_predictions")}
    indexes_feat = {idx["name"] for idx in inspector.get_indexes("v3_feature_snapshots")}
    assert "ix_v3_prediction_fixture_time" in indexes_pred
    assert "ix_v3_prediction_model_version" in indexes_pred
    assert "ix_v3_model_predictions_v3_feature_snapshot_id" in indexes_pred
    assert "ix_v3_feature_snapshot_fixture_time" in indexes_feat


def test_alembic_downgrade_removes_v3_tables(tmp_path: Path, repo_root: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'alembic_v3_down.db'}"
    alembic_cfg = Config(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_cfg, "head")
    engine = create_db_engine(database_url)
    tables_after_upgrade = set(inspect(engine).get_table_names())
    assert "v3_feature_snapshots" in tables_after_upgrade
    assert "v3_model_predictions" in tables_after_upgrade

    command.downgrade(alembic_cfg, "0003_ou_model_tables")
    engine = create_db_engine(database_url)
    tables_after_downgrade = set(inspect(engine).get_table_names())
    assert "v3_feature_snapshots" not in tables_after_downgrade
    assert "v3_model_predictions" not in tables_after_downgrade
    # Ensure earlier OU tables remain in place.
    assert "ou_feature_snapshots" in tables_after_downgrade
    assert "ou_model_predictions" in tables_after_downgrade
