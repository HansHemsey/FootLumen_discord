from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.team_features import (
    build_team_features,
    save_team_feature_snapshot,
)

PREDICTION_TIME = datetime(2026, 5, 2, 12, tzinfo=UTC)


def test_team_features_windows_splits_stats_ewma_and_standings(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'team_features.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_teams(session)
        _seed_target_fixture(session)
        _seed_history_for_primary_team(session)
        _seed_history_for_away_team(session)
        _seed_statistics_and_events(session)
        _seed_standings(session)

        result = build_team_features(session, -900, PREDICTION_TIME)

    features = result.features_json
    quality = result.data_quality_json

    assert features["home_team_global_matches_available_last3"] == 3
    assert features["home_team_home_matches_available_last3"] == 2
    assert features["home_team_away_matches_available_last3"] == 2
    assert features["home_team_global_points_per_match_last3"] == pytest.approx(4 / 3)
    assert features["home_team_home_win_rate_last3"] == pytest.approx(0.5)
    assert features["home_team_global_last3_ppg"] == pytest.approx(4 / 3)
    assert features["home_team_home_last5_ppg"] == pytest.approx(1.5)
    assert features["home_team_global_points_ewma"] is not None
    assert features["home_team_global_shots_total_avg_last3"] == pytest.approx(10.0)
    assert features["home_team_global_shots_on_goal_avg_last3"] == pytest.approx(5.0)
    assert features["home_team_global_shots_for_avg_last3"] == pytest.approx(10.0)
    assert features["home_team_global_shots_against_avg_last3"] == pytest.approx(6.0)
    assert features["home_team_global_possession_avg_last3"] == pytest.approx(55.0)
    assert features["home_team_global_yellow_cards_avg_last3"] == pytest.approx(2.0)
    assert features["home_team_global_pseudo_xg_avg_last3"] == pytest.approx(1.17)
    assert features["home_team_global_shot_accuracy_last3"] == pytest.approx(0.5)
    assert features["home_team_global_goal_conversion_last3"] == pytest.approx(0.4)
    assert features["home_team_global_box_shot_share_last3"] == pytest.approx(0.6)
    assert features["home_team_global_goal_diff_adj_avg_last3"] is not None
    assert "home_team_global_adj_goals_for_last3" in features
    assert features["home_team_rest_days"] == pytest.approx(2.7083333333333335)
    assert features["away_team_travel_away_flag"] == 1
    assert features["fixture_round_number"] is None
    assert features["home_team_standing_rank"] == 2
    assert features["home_team_standing_points_per_match"] == pytest.approx(2.0)
    assert features["rank_diff"] == pytest.approx(-4)
    assert features["points_diff"] == pytest.approx(6)
    assert quality["standings_available_home"] is True
    assert quality["pseudo_xg_available_home"] is True
    assert quality["fixture_statistics_coverage_ratio"] > 0


def test_team_features_exclude_target_and_future_fixtures(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'anti_leakage.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_teams(session)
        _add_fixture(
            session,
            -900,
            datetime(2026, 4, 30, 19, tzinfo=UTC),
            -1,
            -2,
            9,
            0,
            status_short="FT",
        )
        _add_fixture(
            session,
            -901,
            datetime(2026, 4, 20, 19, tzinfo=UTC),
            -1,
            -3,
            1,
            1,
        )
        _add_fixture(
            session,
            -902,
            datetime(2026, 5, 3, 19, tzinfo=UTC),
            -1,
            -3,
            5,
            0,
        )

        result = build_team_features(session, -900, PREDICTION_TIME)

    features = result.features_json
    assert features["home_team_global_matches_available_last3"] == 1
    assert features["home_team_global_points_per_match_last3"] == pytest.approx(1.0)
    assert features["home_team_global_goals_for_avg_last3"] == pytest.approx(1.0)


def test_team_features_ignore_snapshots_after_prediction_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'snapshots.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_teams(session)
        _seed_target_fixture(session)
        _add_fixture(
            session,
            -901,
            datetime(2026, 4, 20, 19, tzinfo=UTC),
            -1,
            -3,
            2,
            0,
        )
        _add_fixture(
            session,
            -911,
            datetime(2026, 4, 21, 19, tzinfo=UTC),
            -2,
            -3,
            1,
            1,
        )
        session.add_all(
            [
                _statistics(
                    -901,
                    -1,
                    datetime(2026, 4, 21, 10, tzinfo=UTC),
                    total_shots=8,
                    shots_on_goal=4,
                ),
                _statistics(
                    -901,
                    -1,
                    datetime(2026, 5, 2, 13, tzinfo=UTC),
                    total_shots=99,
                    shots_on_goal=50,
                ),
            ]
        )

        result = build_team_features(session, -900, PREDICTION_TIME)

    assert result.features_json["home_team_global_shots_total_avg_last3"] == pytest.approx(8.0)
    assert result.features_json["home_team_global_shots_on_goal_avg_last3"] == pytest.approx(4.0)


def test_team_features_missing_optional_data_returns_none_and_warnings(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'missing.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_teams(session)
        _seed_target_fixture(session)
        _add_fixture(
            session,
            -901,
            datetime(2026, 4, 20, 19, tzinfo=UTC),
            -1,
            -3,
            2,
            0,
        )
        _add_fixture(
            session,
            -911,
            datetime(2026, 4, 21, 19, tzinfo=UTC),
            -2,
            -3,
            1,
            1,
        )

        result = build_team_features(session, -900, PREDICTION_TIME)

    features = result.features_json
    quality = result.data_quality_json
    assert features["home_team_global_shots_total_avg_last3"] is None
    assert features["home_team_global_pseudo_xg_avg_last3"] is None
    assert features["home_team_standing_rank"] is None
    assert quality["pseudo_xg_available_home"] is False
    assert quality["standings_available_home"] is False
    assert quality["warnings"]


def test_save_team_feature_snapshot_is_idempotent(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'snapshot.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_teams(session)
        _seed_target_fixture(session)
        _add_fixture(
            session,
            -901,
            datetime(2026, 4, 20, 19, tzinfo=UTC),
            -1,
            -3,
            2,
            0,
        )
        _add_fixture(
            session,
            -911,
            datetime(2026, 4, 21, 19, tzinfo=UTC),
            -2,
            -3,
            1,
            1,
        )

        first = save_team_feature_snapshot(session, -900, PREDICTION_TIME)
        second = save_team_feature_snapshot(session, -900, PREDICTION_TIME)
        snapshot_count = session.scalar(select(func.count()).select_from(models.FeatureSnapshot))

    assert first.id == second.id
    assert snapshot_count == 1
    assert first.feature_version == "team_features_v1"
    assert first.features_json["home_team_global_matches_available_last3"] == 1


def _seed_teams(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-1, name="Synthetic Home", country="Synthetic", payload_json={}),
            models.Team(team_id=-2, name="Synthetic Away", country="Synthetic", payload_json={}),
            models.Team(team_id=-3, name="Synthetic Other", country="Synthetic", payload_json={}),
        ]
    )


def _seed_target_fixture(session) -> None:
    _add_fixture(
        session,
        -900,
        datetime(2026, 5, 2, 20, tzinfo=UTC),
        -1,
        -2,
        None,
        None,
        status_short="NS",
        status="NS",
    )


def _seed_history_for_primary_team(session) -> None:
    _add_fixture(session, -901, datetime(2026, 4, 29, 19, tzinfo=UTC), -1, -3, 2, 0)
    _add_fixture(session, -902, datetime(2026, 4, 25, 19, tzinfo=UTC), -3, -1, 1, 1)
    _add_fixture(session, -903, datetime(2026, 4, 20, 19, tzinfo=UTC), -1, -2, 0, 1)
    _add_fixture(session, -904, datetime(2026, 4, 10, 19, tzinfo=UTC), -2, -1, 2, 3)


def _seed_history_for_away_team(session) -> None:
    _add_fixture(session, -911, datetime(2026, 4, 28, 19, tzinfo=UTC), -2, -3, 1, 1)
    _add_fixture(session, -912, datetime(2026, 4, 24, 19, tzinfo=UTC), -3, -2, 0, 2)
    _add_fixture(session, -913, datetime(2026, 4, 18, 19, tzinfo=UTC), -2, -3, 1, 0)


def _seed_statistics_and_events(session) -> None:
    session.add_all(
        [
            _statistics(
                -901,
                -1,
                datetime(2026, 4, 30, 10, tzinfo=UTC),
                total_shots=10,
                shots_on_goal=5,
                shots_inside_box=6,
                possession="55%",
                passes_total=500,
                corners=4,
                fouls=10,
                goalkeeper_saves=2,
            ),
            _statistics(
                -901,
                -3,
                datetime(2026, 4, 30, 10, tzinfo=UTC),
                total_shots=6,
                shots_on_goal=2,
                shots_inside_box=3,
                possession="45%",
                corners=2,
                goalkeeper_saves=3,
            ),
            _statistics(
                -901,
                -1,
                datetime(2026, 5, 2, 13, tzinfo=UTC),
                total_shots=99,
                shots_on_goal=50,
            ),
            _statistics(
                -911,
                -2,
                datetime(2026, 4, 29, 10, tzinfo=UTC),
                total_shots=7,
                shots_on_goal=3,
                shots_inside_box=4,
                possession="48%",
                corners=3,
            ),
            _card_event(-901, -1, datetime(2026, 4, 30, 10, tzinfo=UTC), "Yellow Card"),
            _card_event(-901, -1, datetime(2026, 4, 30, 10, tzinfo=UTC), "Yellow Card"),
        ]
    )


def _seed_standings(session) -> None:
    session.add_all(
        [
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-1,
                snapshot_date=datetime(2026, 5, 1, 8, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 1, 8, tzinfo=UTC),
                rank=2,
                points=24,
                goals_diff=8,
                all_played=12,
                payload_json={"synthetic": True},
            ),
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-1,
                snapshot_date=datetime(2026, 5, 2, 13, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                rank=1,
                points=27,
                goals_diff=11,
                all_played=13,
                payload_json={"synthetic": True, "future_snapshot": True},
            ),
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-2,
                snapshot_date=datetime(2026, 5, 1, 8, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 1, 8, tzinfo=UTC),
                rank=6,
                points=18,
                goals_diff=1,
                all_played=12,
                payload_json={"synthetic": True},
            ),
        ]
    )


def _add_fixture(
    session,
    fixture_id: int,
    fixture_date: datetime,
    home_team_id: int,
    away_team_id: int,
    home_goals: int | None,
    away_goals: int | None,
    *,
    status_short: str = "FT",
    status: str = "FT",
) -> None:
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=fixture_date,
            timezone="UTC",
            round="Synthetic Round",
            league_id=-100,
            season=2026,
            status=status,
            status_short=status_short,
            status_long="Synthetic status",
            elapsed=90 if status_short == "FT" else None,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team=f"Synthetic Team {home_team_id}",
            away_team=f"Synthetic Team {away_team_id}",
            home_goals=home_goals,
            away_goals=away_goals,
            payload_json={"synthetic": True},
        )
    )


def _statistics(
    fixture_id: int,
    team_id: int,
    fetched_at: datetime,
    *,
    total_shots: int,
    shots_on_goal: int,
    shots_inside_box: int | None = None,
    possession: str | None = None,
    passes_total: int | None = None,
    corners: int | None = None,
    fouls: int | None = None,
    goalkeeper_saves: int | None = None,
) -> models.FixtureStatistics:
    values = [
        {"type": "Total Shots", "value": total_shots},
        {"type": "Shots on Goal", "value": shots_on_goal},
    ]
    optional_values = {
        "Shots insidebox": shots_inside_box,
        "Ball Possession": possession,
        "Total passes": passes_total,
        "Corner Kicks": corners,
        "Fouls": fouls,
        "Goalkeeper Saves": goalkeeper_saves,
    }
    values.extend(
        {"type": stat_type, "value": value}
        for stat_type, value in optional_values.items()
        if value is not None
    )
    return models.FixtureStatistics(
        fixture_id=fixture_id,
        team_id=team_id,
        fetched_at=fetched_at,
        statistics_json=values,
        payload_json={"synthetic": True},
    )


def _card_event(
    fixture_id: int,
    team_id: int,
    fetched_at: datetime,
    detail: str,
) -> models.FixtureEvent:
    return models.FixtureEvent(
        fixture_id=fixture_id,
        team_id=team_id,
        type="Card",
        event_type="Card",
        detail=detail,
        elapsed=45,
        fetched_at=fetched_at,
        payload_json={"synthetic": True},
    )
