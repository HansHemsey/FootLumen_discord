from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from football_predictor.db import models
from football_predictor.db.session import (
    create_db_engine,
    create_session_factory,
    init_db,
    session_scope,
)
from football_predictor.worldcup.enrichment import (
    build_enriched_worldcup_features_for_fixture,
    build_group_state_snapshots,
    build_squad_strength_features,
    build_worldcup_feature_matrix,
    compute_national_elo_snapshots,
    import_fifa_ranking_snapshots,
    ingest_national_results_csv,
    parse_btts_odds_rows,
    point_in_time_reference_features,
)


def test_worldcup_enrichment_tables_created_by_init_db(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'enrichment_schema.db'}")
    init_db(engine)

    tables = set(inspect(engine).get_table_names())

    assert "national_team_aliases" in tables
    assert "national_team_matches" in tables
    assert "national_elo_snapshots" in tables
    assert "fifa_ranking_snapshots" in tables
    assert "worldcup_group_state_snapshots" in tables
    assert "squad_strength_features" in tables


def test_national_results_ingestion_is_idempotent(tmp_path: Path) -> None:
    csv_path = tmp_path / "national_results.csv"
    csv_path.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,neutral\n"
        "2025-01-01,Alpha,Beta,1,0,Friendly,true\n",
        encoding="utf-8",
    )
    engine = create_db_engine(f"sqlite:///{tmp_path / 'national_results.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        first = ingest_national_results_csv(session, csv_path, source="synthetic", write=True)
        second = ingest_national_results_csv(session, csv_path, source="synthetic", write=True)
        rows = session.execute(select(models.NationalTeamMatch)).scalars().all()

    assert first.rows_written == 1
    assert second.rows_written == 1
    assert len(rows) == 1
    assert rows[0].home_team_canonical == "Alpha"


def test_enriched_features_exclude_future_international_matches(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'pit_history.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    prediction_time = datetime(2026, 6, 1, 12, tzinfo=UTC)
    fixture_time = prediction_time + timedelta(days=1)

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=fixture_time)
        session.add_all(
            [
                _national_match(date(2025, 1, 1), "Alpha", "Beta", 1, 0),
                _national_match(date(2026, 6, 2), "Alpha", "Beta", 0, 5),
            ]
        )
        session.flush()

        fixture = session.get(models.Fixture, -1001)
        features = build_enriched_worldcup_features_for_fixture(
            session,
            fixture,
            prediction_time=prediction_time,
        )

    assert features["wc_home_history_count"] == 1
    assert features["wc_home_last5_goals_against_avg"] == pytest.approx(0.0)


def test_fifa_and_elo_snapshots_use_latest_before_cutoff(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'pit_snapshots.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 1, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.FifaRankingSnapshot(
                    canonical_team="Alpha",
                    snapshot_date=date(2026, 5, 1),
                    rank=10,
                    points=1500,
                    source="synthetic",
                    payload_json={},
                ),
                models.FifaRankingSnapshot(
                    canonical_team="Alpha",
                    snapshot_date=date(2026, 6, 2),
                    rank=1,
                    points=2000,
                    source="synthetic",
                    payload_json={},
                ),
                models.NationalEloSnapshot(
                    canonical_team="Alpha",
                    snapshot_date=date(2026, 5, 1),
                    rank=20,
                    elo=1550,
                    source="synthetic",
                    payload_json={},
                ),
                models.NationalEloSnapshot(
                    canonical_team="Alpha",
                    snapshot_date=date(2026, 6, 2),
                    rank=1,
                    elo=1900,
                    source="synthetic",
                    payload_json={},
                ),
            ]
        )
        session.add_all(
            [
                models.FifaRankingSnapshot(
                    canonical_team="Beta",
                    snapshot_date=date(2026, 5, 1),
                    rank=30,
                    points=1300,
                    source="synthetic",
                    payload_json={},
                ),
                models.NationalEloSnapshot(
                    canonical_team="Beta",
                    snapshot_date=date(2026, 5, 1),
                    rank=40,
                    elo=1450,
                    source="synthetic",
                    payload_json={},
                ),
            ]
        )
        features = point_in_time_reference_features(session, "Alpha", "Beta", cutoff)

    assert features["wc_fifa_home_rank"] == 10
    assert features["wc_current_elo_home"] == 1550
    assert features["wc_fifa_rank_diff"] == 20
    assert features["wc_current_elo_diff"] == 100


def test_import_fifa_rankings_requires_explicit_snapshot_date(tmp_path: Path) -> None:
    csv_path = tmp_path / "fifa.csv"
    csv_path.write_text(
        "Classement;Pays;Total de points;Points précédents;+/-\n"
        "1;Alpha;1800;1700;+1\n",
        encoding="utf-8",
    )
    engine = create_db_engine(f"sqlite:///{tmp_path / 'fifa_import.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        result = import_fifa_ranking_snapshots(
            session,
            csv_path,
            snapshot_date=date(2026, 5, 1),
            source="synthetic",
            write=True,
        )
        row = session.execute(select(models.FifaRankingSnapshot)).scalar_one()

    assert result.rows_written == 1
    assert row.snapshot_date == date(2026, 5, 1)
    assert row.canonical_team == "Alpha"


def test_compute_elo_snapshots_from_matches_is_point_in_time(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'elo_compute.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        session.add_all(
            [
                _national_match(date(2025, 1, 1), "Alpha", "Beta", 3, 0),
                _national_match(date(2026, 7, 1), "Beta", "Alpha", 5, 0),
            ]
        )
        result = compute_national_elo_snapshots(
            session,
            snapshot_date=date(2026, 6, 1),
            source="synthetic",
            write=True,
        )
        rows = session.execute(select(models.NationalEloSnapshot)).scalars().all()

    assert result.rows_seen == 1
    assert {row.snapshot_date for row in rows} == {date(2025, 1, 1)}


def test_btts_parser_stores_yes_no_in_existing_odds_shape() -> None:
    fetched_at = datetime(2026, 6, 1, 12, tzinfo=UTC)
    payload = {
        "response": [
            {
                "fixture": {"id": -1001},
                "league": {"id": 1, "season": 2026},
                "bookmakers": [
                    {
                        "id": -1,
                        "name": "Synthetic Book",
                        "bets": [
                            {
                                "id": 8,
                                "name": "Both Teams Score",
                                "values": [
                                    {"value": "Yes", "odd": "1.80"},
                                    {"value": "No", "odd": "2.05"},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    rows = parse_btts_odds_rows(payload, target_bet_id=8, fetched_at=fetched_at)

    assert rows[0]["odd_home"] == 1.80
    assert rows[0]["odd_draw"] is None
    assert rows[0]["odd_away"] == 2.05
    assert rows[0]["payload_json"]["labels"] == {"odd_home": "Yes", "odd_away": "No"}


def test_group_incentives_ignore_results_after_cutoff(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'group_state.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 12, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        _seed_group_teams(session)
        session.add_all(
            [
                _fixture(-2001, "Alpha", "Beta", -1101, -1102, cutoff - timedelta(days=1), 1, 0),
                _fixture(-2002, "Alpha", "Beta", -1101, -1102, cutoff + timedelta(days=1), 0, 9),
            ]
        )
        result = build_group_state_snapshots(session, cutoff=cutoff, write=True)
        alpha = session.execute(
            select(models.WorldCupGroupStateSnapshot).where(
                models.WorldCupGroupStateSnapshot.team_id == -1101
            )
        ).scalar_one()

    assert result.rows_written == 2
    assert alpha.points == 3
    assert alpha.goals_against == 0


def test_squad_strength_uses_only_squads_before_snapshot(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'squad_strength.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    cutoff = datetime(2026, 6, 1, 12, tzinfo=UTC)

    with session_scope(session_factory) as session:
        session.add(models.Team(team_id=-1201, name="Alpha", national=True, payload_json={}))
        session.add_all(
            [
                models.Player(player_id=-1, name="Before", payload_json={}),
                models.Player(player_id=-2, name="After", payload_json={}),
                models.PlayerSquad(
                    player_id=-1,
                    team_id=-1201,
                    league_id=1,
                    season=2026,
                    position="G",
                    fetched_at=cutoff - timedelta(days=1),
                    payload_json={},
                ),
                models.PlayerSquad(
                    player_id=-2,
                    team_id=-1201,
                    league_id=1,
                    season=2026,
                    position="F",
                    fetched_at=cutoff + timedelta(days=1),
                    payload_json={},
                ),
            ]
        )
        build_squad_strength_features(session, snapshot_at=cutoff, write=True)
        row = session.execute(select(models.SquadStrengthFeature)).scalar_one()

    assert row.player_count == 1
    assert row.key_players_json == [{"player_id": -1, "name": "Before", "position": "G"}]


def test_feature_matrix_has_cutoff_audit_and_no_target_scores(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'feature_matrix.db'}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    kickoff = datetime(2026, 6, 11, 20, tzinfo=UTC)

    with session_scope(session_factory) as session:
        _seed_worldcup_fixture(session, kickoff=kickoff)
        frame = build_worldcup_feature_matrix(session, prediction_offset_hours=24)

    assert len(frame) == 1
    assert "wc_feature_cutoff" in frame.columns
    assert "home_goals" not in frame.columns
    assert "away_goals" not in frame.columns
    assert frame.loc[0, "prediction_time"] == "2026-06-10T20:00:00+00:00"


def _national_match(
    match_date: date,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
) -> models.NationalTeamMatch:
    return models.NationalTeamMatch(
        match_date=match_date,
        home_team_canonical=home,
        away_team_canonical=away,
        home_score=home_score,
        away_score=away_score,
        tournament="Friendly",
        competition_type="friendly",
        neutral=True,
        source="synthetic",
        source_match_id=f"{match_date.isoformat()}-{home}-{away}-{home_score}-{away_score}",
        payload_json={"synthetic": True},
    )


def _seed_worldcup_fixture(session, *, kickoff: datetime) -> None:
    session.add_all(
        [
            models.Team(team_id=-1001, name="Alpha", country="Synthetic", national=True),
            models.Team(team_id=-1002, name="Beta", country="Synthetic", national=True),
            models.Fixture(
                fixture_id=-1001,
                date=kickoff,
                timestamp=int(kickoff.timestamp()),
                timezone="UTC",
                round="Group A - 1",
                league_id=1,
                season=2026,
                status="NS",
                status_short="NS",
                home_team_id=-1001,
                away_team_id=-1002,
                home_team="Alpha",
                away_team="Beta",
                payload_json={"synthetic": True},
            ),
        ]
    )
    session.flush()


def _seed_group_teams(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-1101, name="Alpha", country="Synthetic", national=True),
            models.Team(team_id=-1102, name="Beta", country="Synthetic", national=True),
        ]
    )
    session.flush()


def _fixture(
    fixture_id: int,
    home: str,
    away: str,
    home_id: int,
    away_id: int,
    kickoff: datetime,
    home_goals: int,
    away_goals: int,
) -> models.Fixture:
    return models.Fixture(
        fixture_id=fixture_id,
        date=kickoff,
        timestamp=int(kickoff.timestamp()),
        timezone="UTC",
        round="Group A - 2",
        league_id=1,
        season=2026,
        status="FT",
        status_short="FT",
        home_team_id=home_id,
        away_team_id=away_id,
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
        payload_json={"synthetic": True},
    )
