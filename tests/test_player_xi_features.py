from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.xi_features import (
    build_player_xi_features,
    save_player_xi_feature_snapshot,
)

PREDICTION_TIME = datetime(2026, 5, 2, 12, tzinfo=UTC)


def test_player_xi_features_p_start_formation_absences_and_leakage(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'xi.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        result = build_player_xi_features(session, -900, PREDICTION_TIME)

    features = result.features_json
    quality = result.data_quality_json
    home_xi = features["home_team_expected_xi_json"]
    absences = features["home_team_key_absences_json"]

    assert features["home_team_probable_formation"] == "4-3-3"
    assert len(home_xi) == 11
    assert -109 not in {row["player_id"] for row in home_xi}
    assert -109 in {row["player_id"] for row in absences}
    assert features["home_team_absence_impact_score"] > 0
    assert features["home_team_starter_missing_count"] == 1
    assert features["home_team_xi_stability_score"] > 0
    assert features["home_team_bench_depth_score"] is not None
    assert quality["home_team_lineups_available"] == 2
    assert quality["home_team_player_stats_available"] == 2
    assert quality["home_team_reference_fallback_used"] is False

    starter = next(row for row in home_xi if row["player_id"] == -101)
    assert starter["p_start"] > 0.75
    assert starter["position_group"] == "GK"
    late_player_ids = {row["player_id"] for row in home_xi}
    assert -199 not in late_player_ids


def test_player_xi_non_starter_absence_is_damped(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'absence.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        result = build_player_xi_features(session, -900, PREDICTION_TIME)

    absences = result.features_json["home_team_key_absences_json"]
    starter_absence = next(row for row in absences if row["player_id"] == -109)
    non_starter_absence = next(row for row in absences if row["player_id"] == -114)

    assert starter_absence["absence_impact"] > non_starter_absence["absence_impact"]
    assert non_starter_absence["p_start"] < 0.35


def test_player_xi_save_snapshot_is_idempotent(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'xi_snapshot.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        first = save_player_xi_feature_snapshot(session, -900, PREDICTION_TIME)
        second = save_player_xi_feature_snapshot(session, -900, PREDICTION_TIME)
        count = session.scalar(select(func.count()).select_from(models.FeatureSnapshot))

    assert first.id == second.id
    assert count == 1
    assert first.feature_version == "player_xi_features_v1"


def _seed_base(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}),
            models.Team(team_id=-30, name="Synthetic Opponent A", payload_json={"synthetic": True}),
            models.Team(team_id=-40, name="Synthetic Opponent B", payload_json={"synthetic": True}),
        ]
    )
    _seed_players(session, -10, range(-101, -116))
    _seed_players(session, -20, range(-201, -214))
    _fixture(session, -900, datetime(2026, 5, 3, 19, tzinfo=UTC), -10, -20, None, None, "NS")
    _fixture(session, -901, datetime(2026, 4, 26, 19, tzinfo=UTC), -10, -30, 2, 0)
    _fixture(session, -902, datetime(2026, 4, 20, 19, tzinfo=UTC), -40, -10, 1, 3)
    _fixture(session, -911, datetime(2026, 4, 26, 19, tzinfo=UTC), -20, -40, 1, 1)
    _fixture(session, -912, datetime(2026, 4, 20, 19, tzinfo=UTC), -30, -20, 0, 2)
    session.add_all(
        [
            _lineup(
                -901,
                -10,
                "4-3-3",
                _home_starting_ids(),
                datetime(2026, 4, 26, 18, tzinfo=UTC),
            ),
            _lineup(
                -902,
                -10,
                "4-3-3",
                _home_starting_ids(),
                datetime(2026, 4, 20, 18, tzinfo=UTC),
            ),
            _lineup(-901, -10, "3-5-2", [-199], datetime(2026, 5, 2, 13, tzinfo=UTC)),
            _lineup(
                -911,
                -20,
                "4-2-3-1",
                list(range(-201, -212)),
                datetime(2026, 4, 26, 18, tzinfo=UTC),
            ),
            _lineup(
                -912,
                -20,
                "4-2-3-1",
                list(range(-201, -212)),
                datetime(2026, 4, 20, 18, tzinfo=UTC),
            ),
        ]
    )
    for fixture_id in (-901, -902):
        for player_id in _home_starting_ids():
            if player_id == -109:
                session.add(
                    _player_stat(fixture_id, -10, player_id, minutes=90, rating=8.2, goals=1)
                )
            else:
                session.add(_player_stat(fixture_id, -10, player_id, minutes=90, rating=7.0))
        session.add(_player_stat(fixture_id, -10, -112, minutes=20, rating=6.0))
    for fixture_id in (-911, -912):
        for player_id in range(-201, -212):
            session.add(_player_stat(fixture_id, -20, player_id, minutes=75, rating=6.5))
    session.add_all(
        [
            models.Injury(
                fixture_id=-900,
                team_id=-10,
                player_id=-109,
                league_id=-100,
                season=2026,
                type="Missing Fixture",
                reason="Synthetic starter injury",
                fetched_at=datetime(2026, 5, 2, 8, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.Injury(
                fixture_id=-900,
                team_id=-10,
                player_id=-114,
                league_id=-100,
                season=2026,
                type="Missing Fixture",
                reason="Synthetic bench injury",
                fetched_at=datetime(2026, 5, 2, 8, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.Injury(
                fixture_id=-900,
                team_id=-10,
                player_id=-101,
                league_id=-100,
                season=2026,
                type="Missing Fixture",
                reason="Synthetic future injury ignored",
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
        ]
    )


def _seed_players(session, team_id: int, player_ids) -> None:
    positions = ["Goalkeeper", "Defender", "Defender", "Defender", "Defender", "Midfielder",
                 "Midfielder", "Midfielder", "Attacker", "Attacker", "Attacker", "Attacker",
                 "Midfielder", "Defender", "Goalkeeper"]
    for index, player_id in enumerate(player_ids):
        position = positions[index % len(positions)]
        session.add(
            models.Player(
                player_id=player_id,
                name=f"Synthetic Player {player_id}",
                payload_json={"synthetic": True},
            )
        )
        session.add(
            models.PlayerSquad(
                team_id=team_id,
                player_id=player_id,
                league_id=-100,
                season=2026,
                position=position,
                number=index + 1,
                fetched_at=datetime(2026, 4, 1, tzinfo=UTC),
                payload_json={"synthetic": True},
            )
        )


def _fixture(
    session,
    fixture_id: int,
    date: datetime,
    home_team_id: int,
    away_team_id: int,
    home_goals: int | None,
    away_goals: int | None,
    status_short: str = "FT",
) -> None:
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=date,
            timezone="UTC",
            round="Synthetic Round",
            league_id=-100,
            season=2026,
            status=status_short,
            status_short=status_short,
            status_long="Synthetic",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team=f"Synthetic {home_team_id}",
            away_team=f"Synthetic {away_team_id}",
            home_goals=home_goals,
            away_goals=away_goals,
            payload_json={"synthetic": True},
        )
    )


def _lineup(
    fixture_id: int,
    team_id: int,
    formation: str,
    player_ids: list[int],
    fetched_at: datetime,
) -> models.FixtureLineup:
    return models.FixtureLineup(
        fixture_id=fixture_id,
        team_id=team_id,
        formation=formation,
        start_xi_json=[
            {
                "player": {
                    "id": player_id,
                    "name": f"Synthetic Player {player_id}",
                    "pos": _pos(player_id),
                    "grid": _grid(index),
                }
            }
            for index, player_id in enumerate(player_ids)
        ],
        substitutes_json=[
            {"player": {"id": -112, "name": "Synthetic Player -112", "pos": "F", "grid": None}},
            {"player": {"id": -113, "name": "Synthetic Player -113", "pos": "M", "grid": None}},
            {"player": {"id": -114, "name": "Synthetic Player -114", "pos": "D", "grid": None}},
        ],
        fetched_at=fetched_at,
        payload_json={"synthetic": True},
    )


def _player_stat(
    fixture_id: int,
    team_id: int,
    player_id: int,
    *,
    minutes: int,
    rating: float,
    goals: int = 0,
) -> models.FixturePlayerStats:
    return models.FixturePlayerStats(
        fixture_id=fixture_id,
        team_id=team_id,
        player_id=player_id,
        fetched_at=datetime(2026, 4, 27, 9, tzinfo=UTC),
        statistics_json=[
            {
                "games": {"minutes": minutes, "position": _pos(player_id), "rating": str(rating)},
                "goals": {"total": goals, "assists": 0},
                "shots": {"total": 3, "on": 1},
            }
        ],
        rating=rating,
        minutes=minutes,
        position=_pos(player_id),
        payload_json={"synthetic": True},
    )


def _home_starting_ids() -> list[int]:
    return [-101, -102, -103, -104, -105, -106, -107, -108, -109, -110, -111]


def _pos(player_id: int) -> str:
    offset = abs(player_id) % 100
    if offset == 1:
        return "G"
    if offset in {2, 3, 4, 5, 14}:
        return "D"
    if offset in {6, 7, 8, 13}:
        return "M"
    return "F"


def _grid(index: int) -> str:
    row = 1 if index == 0 else 2 + (index // 4)
    col = 1 + (index % 4)
    return f"{row}:{col}"
