from __future__ import annotations

from datetime import UTC, datetime

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.player_features import (
    build_player_recent_form,
    compute_player_value,
)
from football_predictor.reference.loaders import load_players_reference

PREDICTION_TIME = datetime(2026, 5, 2, 12, tzinfo=UTC)


def test_build_player_recent_form_uses_only_point_in_time_rows(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'player_form.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        form = build_player_recent_form(session, -10, PREDICTION_TIME, windows=(3, 5))

    starter = form[-101]
    assert starter["minutes_recent_last3"] == 270
    assert starter["starts_recent_last3"] == 3
    assert starter["average_rating_last3"] == 7.5
    attacker = form[-109]
    creator = form[-106]
    assert attacker["goals_last3"] >= 1
    assert creator["assists_last3"] >= 1
    assert starter["cards_last3"] == 1
    assert starter["last_match_minutes"] == 90
    assert starter["ewma_minutes"] == 90
    assert -199 not in form


def test_compute_player_value_normalizes_within_position_and_tolerates_missing_rating(
    tmp_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'player_value.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        value = compute_player_value(session, -101, -10, PREDICTION_TIME)
        missing_rating_value = compute_player_value(session, -114, -10, PREDICTION_TIME)

    assert value["position_group"] == "GK"
    assert 0 <= value["value_0_100"] <= 100
    assert value["rating_available"] is True
    assert missing_rating_value["rating_available"] is False
    assert 0 <= missing_rating_value["value_0_100"] <= 100


def test_player_recent_form_uses_players_reference_fallback(
    tmp_path,
    players_reference_sample_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'player_reference.db'}")
    session_factory = create_session_factory(engine)
    players_reference = load_players_reference(players_reference_sample_path)

    with session_scope(session_factory) as session:
        session.add(models.Team(team_id=77, name="Angers", payload_json={}))
        form = build_player_recent_form(
            session,
            77,
            PREDICTION_TIME,
            players_reference=players_reference,
        )

    assert {455243, 191289} <= set(form)
    assert form[455243]["position_group"] == "ATT"
    assert form[455243]["minutes_recent_last3"] == 0


def _seed_team_history(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}),
            models.Team(team_id=-30, name="Synthetic Opponent A", payload_json={"synthetic": True}),
            models.Team(team_id=-40, name="Synthetic Opponent B", payload_json={"synthetic": True}),
        ]
    )
    _seed_players(session, -10, range(-101, -116, -1))
    _fixture(session, -1000, datetime(2026, 5, 3, 19, tzinfo=UTC), -10, -20, None, None, "NS")
    for index, fixture_id in enumerate((-1001, -1002, -1003)):
        _fixture(
            session,
            fixture_id,
            datetime(2026, 4, 28 - index * 3, 19, tzinfo=UTC),
            -10 if index != 1 else -30,
            -30 if index != 1 else -10,
            2,
            1,
        )
        session.add(
            _lineup(
                fixture_id,
                -10,
                "4-3-3",
                _starting_ids(),
                datetime(2026, 4, 28 - index * 3, 18, tzinfo=UTC),
            )
        )
        session.add(_player_stat(fixture_id, -10, -101, 90, 7.5, "G"))
        session.add(_player_stat(fixture_id, -10, -109, 88, 7.2, "F", goals=1))
        session.add(_player_stat(fixture_id, -10, -114, 15, None, "D"))
    session.add(
        _lineup(-1001, -10, "3-5-2", [-199], datetime(2026, 5, 2, 13, tzinfo=UTC))
    )
    session.add(
        models.FixtureEvent(
            fixture_id=-1001,
            team_id=-10,
            player_id=-109,
            assist_player_id=-106,
            type="Goal",
            detail="Normal Goal",
            fetched_at=datetime(2026, 4, 29, 8, tzinfo=UTC),
            payload_json={"synthetic": True},
        )
    )
    session.add(
        models.FixtureEvent(
            fixture_id=-1002,
            team_id=-10,
            player_id=-101,
            type="Card",
            detail="Yellow Card",
            fetched_at=datetime(2026, 4, 26, 8, tzinfo=UTC),
            payload_json={"synthetic": True},
        )
    )


def _seed_players(session, team_id: int, player_ids) -> None:
    positions = [
        "Goalkeeper",
        "Defender",
        "Defender",
        "Defender",
        "Defender",
        "Midfielder",
        "Midfielder",
        "Midfielder",
        "Attacker",
        "Attacker",
        "Attacker",
        "Attacker",
        "Midfielder",
        "Defender",
        "Goalkeeper",
    ]
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
                    "grid": f"1:{index + 1}",
                }
            }
            for index, player_id in enumerate(player_ids)
        ],
        substitutes_json=[],
        fetched_at=fetched_at,
        payload_json={"synthetic": True},
    )


def _player_stat(
    fixture_id: int,
    team_id: int,
    player_id: int,
    minutes: int,
    rating: float | None,
    position: str,
    *,
    goals: int = 0,
) -> models.FixturePlayerStats:
    return models.FixturePlayerStats(
        fixture_id=fixture_id,
        team_id=team_id,
        player_id=player_id,
        fetched_at=datetime(2026, 4, 30, 9, tzinfo=UTC),
        statistics_json=[
            {
                "games": {"minutes": minutes, "position": position, "rating": rating},
                "goals": {"total": goals, "assists": 0},
            }
        ],
        rating=rating,
        minutes=minutes,
        position=position,
        payload_json={"synthetic": True},
    )


def _starting_ids() -> list[int]:
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
