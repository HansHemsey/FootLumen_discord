from __future__ import annotations

from datetime import UTC, datetime

from test_player_features import PREDICTION_TIME, _seed_team_history

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.availability_features import (
    compute_absence_impact,
    parse_injury_severity,
)


def test_parse_injury_severity_maps_common_statuses() -> None:
    assert parse_injury_severity({"type": "Missing Fixture"}) == 1.0
    assert parse_injury_severity({"type": "Questionable"}) == 0.6
    assert parse_injury_severity({"reason": "minor knock"}) == 0.3
    assert parse_injury_severity({}) == 0.3


def test_compute_absence_impact_weights_starter_more_than_bench_and_ignores_future(
    tmp_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'availability.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        session.add_all(
            [
                models.Injury(
                    fixture_id=-1000,
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
                    fixture_id=-1000,
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
                    fixture_id=-1000,
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
        impact = compute_absence_impact(session, -10, -1000, PREDICTION_TIME)

    absences = impact["key_absences_json"]
    starter_absence = next(row for row in absences if row["player_id"] == -109)
    bench_absence = next(row for row in absences if row["player_id"] == -114)

    assert impact["absent_expected_starters_count"] == 1
    assert impact["absence_impact_score"] > 0
    assert impact["availability_score"] < 1.0
    assert impact["replacement_quality_score"] <= 1.0
    assert starter_absence["absence_impact"] > bench_absence["absence_impact"]
    assert -101 not in {row["player_id"] for row in absences}


def test_compute_absence_impact_ignores_future_generic_team_injury(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'future_generic_injury.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_team_history(session)
        session.add(
            models.Injury(
                fixture_id=None,
                team_id=-10,
                player_id=-109,
                league_id=-100,
                season=2026,
                type="Missing Fixture",
                reason="Synthetic generic future injury ignored",
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            )
        )
        impact = compute_absence_impact(session, -10, -1000, PREDICTION_TIME)

    assert impact["absent_expected_starters_count"] == 0
    assert impact["key_absences_json"] == []
