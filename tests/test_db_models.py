from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.repositories import (
    insert_raw_api_snapshot,
    upsert_fixture,
    upsert_league,
    upsert_team,
)
from football_predictor.db.session import create_session_factory, session_scope


def test_create_db_and_tables_creates_expected_schema(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'models.db'}")
    inspector = inspect(engine)

    assert _columns(inspector, "raw_api_snapshots") >= {
        "id",
        "endpoint",
        "params_json",
        "payload_json",
        "fetched_at",
        "status_code",
        "source",
    }
    assert _columns(inspector, "leagues") >= {
        "league_id",
        "name",
        "country",
        "type",
        "logo",
        "payload_json",
    }
    assert _columns(inspector, "venues") >= {
        "venue_id",
        "name",
        "address",
        "city",
        "capacity",
        "surface",
        "image",
        "payload_json",
    }
    assert _columns(inspector, "teams") >= {
        "team_id",
        "name",
        "country",
        "founded",
        "logo",
        "venue_id",
        "payload_json",
    }
    assert _columns(inspector, "fixtures") >= {
        "fixture_id",
        "league_id",
        "season",
        "round",
        "date",
        "timezone",
        "status_short",
        "status_long",
        "elapsed",
        "home_team_id",
        "away_team_id",
        "home_goals",
        "away_goals",
        "venue_id",
        "payload_json",
    }
    assert _columns(inspector, "standing_snapshots") >= {
        "league_id",
        "season",
        "team_id",
        "rank",
        "points",
        "goals_diff",
        "form",
        "description",
        "all_played",
        "all_win",
        "all_draw",
        "all_lose",
        "all_goals_for",
        "all_goals_against",
        "home_played",
        "home_win",
        "home_draw",
        "home_lose",
        "away_played",
        "away_win",
        "away_draw",
        "away_lose",
        "snapshot_date",
        "payload_json",
    }
    assert _columns(inspector, "fixture_statistics") >= {
        "fixture_id",
        "team_id",
        "statistics_json",
        "fetched_at",
    }
    assert _columns(inspector, "fixture_events") >= {
        "fixture_id",
        "team_id",
        "player_id",
        "assist_player_id",
        "type",
        "detail",
        "elapsed",
        "extra",
        "payload_json",
    }
    assert _columns(inspector, "fixture_lineups") >= {
        "fixture_id",
        "team_id",
        "coach_id",
        "formation",
        "start_xi_json",
        "substitutes_json",
        "payload_json",
        "fetched_at",
    }
    assert _columns(inspector, "fixture_player_stats") >= {
        "fixture_id",
        "team_id",
        "player_id",
        "statistics_json",
        "rating",
        "minutes",
        "position",
        "payload_json",
        "fetched_at",
    }
    assert _columns(inspector, "players") >= {
        "player_id",
        "name",
        "firstname",
        "lastname",
        "age",
        "birth_date",
        "nationality",
        "height",
        "weight",
        "injured",
        "photo",
        "payload_json",
    }
    assert _columns(inspector, "player_squads") >= {
        "team_id",
        "player_id",
        "position",
        "number",
        "payload_json",
        "fetched_at",
    }
    assert _columns(inspector, "injuries") >= {
        "fixture_id",
        "league_id",
        "season",
        "team_id",
        "player_id",
        "reason",
        "type",
        "date",
        "payload_json",
        "fetched_at",
    }
    assert _columns(inspector, "odds_snapshots") >= {
        "fixture_id",
        "league_id",
        "season",
        "bookmaker_id",
        "bookmaker_name",
        "bet_id",
        "bet_name",
        "values_json",
        "fetched_at",
        "payload_json",
    }
    assert _columns(inspector, "api_prediction_snapshots") >= {
        "fixture_id",
        "winner_team_id",
        "win_or_draw",
        "advice",
        "percent_home",
        "percent_draw",
        "percent_away",
        "payload_json",
        "fetched_at",
    }
    assert _columns(inspector, "feature_snapshots") >= {
        "fixture_id",
        "prediction_time",
        "feature_version",
        "features_json",
        "data_quality_json",
        "created_at",
    }
    assert _columns(inspector, "model_predictions") >= {
        "fixture_id",
        "prediction_time",
        "model_version",
        "p_home",
        "p_draw",
        "p_away",
        "predicted_outcome",
        "confidence",
        "feature_snapshot_id",
        "explanation_json",
        "created_at",
    }
    assert _columns(inspector, "discord_messages") >= {
        "fixture_id",
        "model_prediction_id",
        "webhook_url_hash",
        "message_hash",
        "competition_key",
        "league_id",
        "season",
        "channel_key",
        "message_type",
        "dry_run",
        "print_only",
        "webhook_hash",
        "route_json",
        "payload_json",
        "sent_at",
        "status",
        "response_text",
    }


def test_repository_upserts_and_raw_snapshot_insert_are_idempotent_ready(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'repositories.db'}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 5, 2, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        # Synthetic DB-only IDs. They are not API-Football examples.
        upsert_league(
            session,
            league_id=-1,
            season=2026,
            values={"name": "Synthetic League", "type": "League", "payload_json": {}},
        )
        upsert_league(
            session,
            league_id=-1,
            season=2026,
            values={"name": "Synthetic League Updated", "type": "League", "payload_json": {}},
        )
        session.add(models.Venue(venue_id=-1, name="Synthetic Venue", address="Synthetic Road"))
        upsert_team(
            session,
            team_id=-10,
            values={"name": "Synthetic Home", "venue_id": -1, "payload_json": {}},
        )
        upsert_team(
            session,
            team_id=-20,
            values={"name": "Synthetic Away", "venue_id": -1, "payload_json": {}},
        )
        upsert_fixture(
            session,
            fixture_id=-100,
            values={
                "league_id": -1,
                "season": 2026,
                "round": "Synthetic Round",
                "date": now,
                "timezone": "UTC",
                "status_short": "NS",
                "status_long": "Not Started",
                "home_team_id": -10,
                "away_team_id": -20,
                "home_team": "Synthetic Home",
                "away_team": "Synthetic Away",
                "home_goals": None,
                "away_goals": None,
                "goals_home": None,
                "goals_away": None,
                "venue_id": -1,
                "payload_json": {"synthetic": True},
            },
        )
        insert_raw_api_snapshot(
            session,
            endpoint="/synthetic",
            params_json={"synthetic": True},
            payload_json={"response": []},
            fetched_at=now,
            status_code=200,
        )

    with session_scope(session_factory) as session:
        leagues = list(session.execute(select(models.League)).scalars())
        fixtures = list(session.execute(select(models.Fixture)).scalars())
        snapshots = list(session.execute(select(models.RawApiSnapshot)).scalars())

    assert len(leagues) == 1
    assert leagues[0].name == "Synthetic League Updated"
    assert len(fixtures) == 1
    assert fixtures[0].home_goals is None
    assert len(snapshots) == 1
    assert snapshots[0].fetched_at is not None


def test_dynamic_snapshot_and_prediction_models_insert_on_sqlite(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'dynamic.db'}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 5, 2, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        # Synthetic DB-only IDs. They are not API-Football examples.
        session.add(models.Venue(venue_id=-1, name="Synthetic Venue"))
        session.add(models.Team(team_id=-10, name="Synthetic Home", payload_json={}))
        session.add(models.Team(team_id=-20, name="Synthetic Away", payload_json={}))
        session.add(models.Player(player_id=-30, name="Synthetic Player", payload_json={}))
        session.add(
            models.Fixture(
                fixture_id=-100,
                league_id=-1,
                season=2026,
                date=now,
                status_short="NS",
                status_long="Not Started",
                home_team_id=-10,
                away_team_id=-20,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={},
            )
        )
        session.flush()
        session.add_all(
            [
                models.StandingSnapshot(
                    league_id=-1,
                    season=2026,
                    team_id=-10,
                    rank=1,
                    points=10,
                    snapshot_date=now,
                    fetched_at=now,
                    payload_json={},
                ),
                models.FixtureStatistics(
                    fixture_id=-100,
                    team_id=-10,
                    statistics_json={"shots": 1},
                    fetched_at=now,
                    payload_json={},
                ),
                models.FixtureEvent(
                    fixture_id=-100,
                    team_id=-10,
                    player_id=-30,
                    assist_player_id=None,
                    type="Goal",
                    detail="Synthetic",
                    elapsed=10,
                    extra=None,
                    fetched_at=now,
                    payload_json={},
                ),
                models.FixtureLineup(
                    fixture_id=-100,
                    team_id=-10,
                    coach_id=-40,
                    formation="4-3-3",
                    start_xi_json=[],
                    substitutes_json=[],
                    payload_json={},
                    fetched_at=now,
                ),
                models.FixturePlayerStats(
                    fixture_id=-100,
                    team_id=-10,
                    player_id=-30,
                    statistics_json={"minutes": 90},
                    rating=7.0,
                    minutes=90,
                    position="Midfielder",
                    payload_json={},
                    fetched_at=now,
                ),
                models.PlayerSquad(
                    team_id=-10,
                    player_id=-30,
                    league_id=-1,
                    season=2026,
                    position="Midfielder",
                    number=8,
                    payload_json={},
                    fetched_at=now,
                ),
                models.Injury(
                    fixture_id=-100,
                    league_id=-1,
                    season=2026,
                    team_id=-10,
                    player_id=-30,
                    reason="Synthetic reason",
                    type="Synthetic type",
                    date=now,
                    payload_json={},
                    fetched_at=now,
                ),
                models.OddsSnapshot(
                    fixture_id=-100,
                    league_id=-1,
                    season=2026,
                    bookmaker_id=None,
                    bookmaker_name="Synthetic Bookmaker",
                    bet_id=None,
                    bet_name="Synthetic Bet",
                    values_json=[],
                    fetched_at=now,
                    payload_json={},
                ),
                models.ApiPredictionSnapshot(
                    fixture_id=-100,
                    winner_team_id=-10,
                    win_or_draw=True,
                    advice="Synthetic advice",
                    percent_home=40.0,
                    percent_draw=30.0,
                    percent_away=30.0,
                    payload_json={},
                    fetched_at=now,
                ),
            ]
        )
        feature_snapshot = models.FeatureSnapshot(
            fixture_id=-100,
            prediction_time=now,
            feature_version="synthetic-v1",
            features_json={},
            data_quality_json={},
        )
        session.add(feature_snapshot)
        session.flush()
        prediction = models.ModelPrediction(
            fixture_id=-100,
            prediction_time=now,
            model_version="synthetic-model",
            p_home=0.4,
            p_draw=0.3,
            p_away=0.3,
            predicted_outcome="HOME",
            predicted_result="HOME",
            confidence=10.0,
            confidence_label="Low",
            confidence_score=10.0,
            feature_snapshot_id=feature_snapshot.id,
            explanation_json=["synthetic"],
            explanations_json=["synthetic"],
        )
        session.add(prediction)
        session.flush()
        session.add(
            models.DiscordMessage(
                fixture_id=-100,
                model_prediction_id=prediction.id,
                webhook_url_hash="abcd1234",
                message_hash="synthetic-message-hash",
                sent_at=now,
                status="sent",
                message_markdown="synthetic markdown",
                response_text="ok",
            )
        )

    with session_scope(session_factory) as session:
        assert session.scalar(select(models.ModelPrediction)) is not None
        assert session.scalar(select(models.DiscordMessage)) is not None
        assert session.scalar(select(models.ApiPredictionSnapshot)) is not None


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}
