from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, select

from alembic import command
from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)


def test_init_db_creates_sprint_3_tables_and_columns(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'schema.db'}")

    init_db(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "raw_api_snapshots",
        "leagues",
        "teams",
        "venues",
        "fixtures",
        "standing_snapshots",
        "bookmakers",
        "bets",
        "players",
        "player_squads",
        "odds_snapshots",
        "feature_snapshots",
        "model_predictions",
        "discord_messages",
    }.issubset(tables)

    assert _has_columns(inspector, "fixtures", {"fixture_id", "status", "status_short"})
    assert _has_columns(
        inspector,
        "odds_snapshots",
        {"odd_home", "odd_draw", "odd_away", "odds_json", "payload_json", "fetched_at"},
    )
    assert _has_columns(inspector, "fixture_lineups", {"players_json", "payload_json"})
    assert _has_columns(inspector, "fixture_player_stats", {"stats_json", "payload_json"})
    assert _has_columns(inspector, "api_prediction_snapshots", {"source", "fetched_at"})
    assert _has_columns(inspector, "model_predictions", {"feature_snapshot_id"})
    assert _is_not_nullable(inspector, "fixture_statistics", "fetched_at")
    assert _is_not_nullable(inspector, "injuries", "fetched_at")
    assert _is_not_nullable(inspector, "odds_snapshots", "fetched_at")


def test_snapshot_and_prediction_records_can_be_inserted(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'records.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    now = datetime(2026, 5, 2, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        # Synthetic DB-only IDs. They are not API-Football examples.
        session.add(models.Venue(venue_id=-1, name="Synthetic Venue"))
        session.add(
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True})
        )
        session.add(
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True})
        )
        session.add(
            models.Fixture(
                fixture_id=-100,
                date=now,
                league_id=-30,
                season=2026,
                venue_id=-1,
                status="NS",
                status_short="NS",
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={"synthetic": True},
            )
        )
        feature_snapshot = models.FeatureSnapshot(
            fixture_id=-100,
            prediction_time=now,
            feature_version="synthetic-v1",
            features_json={"synthetic": True},
            data_quality_json={"source": "synthetic"},
        )
        session.add(feature_snapshot)
        session.flush()

        session.add_all(
            [
                models.RawApiSnapshot(
                    endpoint="/synthetic",
                    params_json={"synthetic": True},
                    payload_json={"response": []},
                    fetched_at=now,
                    status_code=200,
                ),
                models.OddsSnapshot(
                    fixture_id=-100,
                    fetched_at=now,
                    is_live=False,
                    odd_home=2.0,
                    odd_draw=3.0,
                    odd_away=4.0,
                    odds_json={"synthetic": True},
                    payload_json={"synthetic": True},
                ),
                models.ApiPredictionSnapshot(
                    fixture_id=-100,
                    fetched_at=now,
                    source="synthetic",
                    payload_json={"synthetic": True},
                ),
                models.ModelPrediction(
                    fixture_id=-100,
                    feature_snapshot_id=feature_snapshot.id,
                    prediction_time=now,
                    model_version="synthetic-model",
                    p_home=0.4,
                    p_draw=0.3,
                    p_away=0.3,
                    predicted_result="HOME",
                    confidence_label="Low",
                    confidence_score=10.0,
                ),
            ]
        )

    with session_scope(session_factory) as session:
        prediction = session.scalar(select(models.ModelPrediction))
        odds = session.scalar(select(models.OddsSnapshot))
        api_prediction = session.scalar(select(models.ApiPredictionSnapshot))

    assert prediction is not None
    assert prediction.feature_snapshot_id is not None
    assert odds is not None
    assert odds.odd_home == 2.0
    assert api_prediction is not None
    assert api_prediction.source == "synthetic"


def test_upsert_by_fields_is_idempotent(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'upsert.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        first = upsert_by_fields(
            session,
            models.Bookmaker,
            {"bookmaker_id": -1},
            {"name": "Synthetic Bookmaker", "payload_json": {"version": 1}},
        )
        second = upsert_by_fields(
            session,
            models.Bookmaker,
            {"bookmaker_id": -1},
            {"name": "Synthetic Bookmaker Updated", "payload_json": {"version": 2}},
        )
        session.flush()
        assert first is second

    with session_scope(session_factory) as session:
        rows = list(session.execute(select(models.Bookmaker)).scalars())

    assert len(rows) == 1
    assert rows[0].name == "Synthetic Bookmaker Updated"


def test_alembic_upgrade_head_creates_initial_schema(tmp_path: Path, repo_root: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'alembic.db'}"
    alembic_cfg = Config(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_cfg, "head")

    engine = create_db_engine(database_url)
    tables = set(inspect(engine).get_table_names())

    assert "alembic_version" in tables
    assert "fixtures" in tables
    assert "model_predictions" in tables
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("discord_messages")}
    assert {
        "v3_model_prediction_id",
        "ou_model_prediction_id",
        "dedupe_key",
    }.issubset(columns)
    indexes = {index["name"] for index in inspector.get_indexes("discord_messages")}
    assert {
        "ix_discord_messages_v3_model_prediction_id",
        "ix_discord_messages_ou_model_prediction_id",
        "ix_discord_messages_dedupe_key",
    }.issubset(indexes)


def test_alembic_downgrade_removes_discord_prediction_links(
    tmp_path: Path,
    repo_root: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'alembic_discord_links_down.db'}"
    alembic_cfg = Config(str(repo_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_cfg, "head")
    engine = create_db_engine(database_url)
    columns_after_upgrade = {
        column["name"] for column in inspect(engine).get_columns("discord_messages")
    }
    assert "v3_model_prediction_id" in columns_after_upgrade
    assert "ou_model_prediction_id" in columns_after_upgrade
    assert "dedupe_key" in columns_after_upgrade

    command.downgrade(alembic_cfg, "0004_v3_model_tables")
    engine = create_db_engine(database_url)
    columns_after_downgrade = {
        column["name"] for column in inspect(engine).get_columns("discord_messages")
    }
    assert "v3_model_prediction_id" not in columns_after_downgrade
    assert "ou_model_prediction_id" not in columns_after_downgrade
    assert "dedupe_key" not in columns_after_downgrade


def _has_columns(inspector, table_name: str, expected_columns: set[str]) -> bool:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return expected_columns.issubset(columns)


def _is_not_nullable(inspector, table_name: str, column_name: str) -> bool:
    columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    return columns[column_name]["nullable"] is False
