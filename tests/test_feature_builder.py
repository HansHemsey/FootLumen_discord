from __future__ import annotations

from datetime import UTC, datetime, timedelta

from test_player_xi_features import PREDICTION_TIME, _home_starting_ids, _lineup, _seed_base

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.feature_builder import build_feature_snapshot
from football_predictor.ou_model.features.h2h_features import build_h2h_features
from football_predictor.ou_model.features.ou_feature_builder import build_ou_feature_snapshot


def test_feature_builder_creates_snapshot_and_flat_features_without_target(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v1")

    assert result.snapshot.id is not None
    assert result.snapshot.feature_version == "v1"
    assert result.features_json["fixture_id"] == -900
    assert result.features_json["league_id"] == -100
    assert result.features_json["season"] == 2026
    assert result.features_json["home_team_id"] == -10
    assert result.features_json["away_team_id"] == -20
    assert "target" not in result.features_json
    assert "home_goals" not in result.features_json
    assert "away_goals" not in result.features_json
    assert 0 <= result.data_quality_json["overall_data_quality_score"] <= 100
    assert result.data_quality_json["historical_matches_home_count"] > 0
    assert result.data_quality_json["historical_matches_away_count"] > 0
    assert "target_lineups_available_flag" in result.data_quality_json
    assert "historical_lineups_available_flag" in result.data_quality_json
    assert "historical_player_stats_available_rate" in result.data_quality_json
    assert result.data_quality_json["data_quality_version"] == "dq_v2"
    assert 0 <= result.data_quality_json["publication_data_quality_score"] <= 100
    assert result.features_json["publication_data_quality_score"] == (
        result.data_quality_json["publication_data_quality_score"]
    )


def test_feature_builder_anti_leakage_filters_future_snapshots(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder_leakage.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v1")

    features = result.features_json
    assert features["market_home"] < 0.9
    assert features["api_pred_home"] == 0.45
    assert features["api_pred_winner_home_flag"] is True
    assert features["api_pred_winner_away_flag"] is False
    assert features["api_pred_win_or_draw_flag"] is True
    assert features["home_team_standing_rank"] == 2
    assert -199 not in {row["player_id"] for row in features["home_team_expected_xi_json"]}
    assert -101 not in {row["player_id"] for row in features["home_team_key_absences_json"]}
    quality = result.data_quality_json["source_quality_json"]
    assert quality["odds_1x2"]["latest_fetched_at"] == "2026-05-02T09:00:00+00:00"
    assert quality["api_prediction"]["latest_fetched_at"] == "2026-05-02T09:00:00+00:00"
    assert quality["standings"]["latest_fetched_at"] == "2026-05-02T08:00:00+00:00"
    assert "future_snapshot_ignored" not in quality["odds_1x2"]["warnings"]


def test_feature_builder_counts_target_lineups_only_before_prediction_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder_lineups.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        session.add_all(
            [
                _lineup(-900, -10, "4-3-3", _home_starting_ids(), PREDICTION_TIME),
                _lineup(-900, -20, "4-2-3-1", list(range(-201, -212)), PREDICTION_TIME),
            ]
        )
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v1")

    assert result.data_quality_json["target_lineups_home_available_flag"] is True
    assert result.data_quality_json["target_lineups_away_available_flag"] is True
    assert result.data_quality_json["target_lineups_available_flag"] is True
    assert result.data_quality_json["lineups_available_flag"] is True


def test_feature_builder_ignores_target_lineups_after_prediction_time(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder_future_lineups.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        fetched_after_cutoff = PREDICTION_TIME + timedelta(seconds=1)
        session.add_all(
            [
                _lineup(-900, -10, "4-3-3", _home_starting_ids(), fetched_after_cutoff),
                _lineup(-900, -20, "4-2-3-1", list(range(-201, -212)), fetched_after_cutoff),
            ]
        )
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v1")

    assert result.data_quality_json["target_lineups_available_flag"] is False


def test_feature_builder_empty_raw_snapshots_mark_sources_checked(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder_raw_checked.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        session.flush()
        session.query(models.Injury).delete()
        for endpoint in ("/fixtures/lineups", "/injuries", "/predictions"):
            session.add(
                models.RawApiSnapshot(
                    endpoint=endpoint,
                    params_json={"fixture": -900},
                    payload_json={"response": []},
                    fetched_at=PREDICTION_TIME - timedelta(minutes=20),
                    status_code=204,
                    source="api-football",
                )
            )
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v1")

    source_quality = result.data_quality_json["source_quality_json"]
    assert source_quality["injuries"]["checked"] is True
    assert source_quality["injuries"]["available"] is False
    assert source_quality["target_lineups"]["checked"] is True
    assert source_quality["target_lineups"]["available"] is False
    assert source_quality["api_prediction"]["checked"] is True
    assert source_quality["api_prediction"]["available"] is False


def test_feature_builder_v3_adds_m30_features_and_quality_flags(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'feature_builder_v3.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        session.add_all(
            [
                _lineup(-900, -10, "4-3-3", _home_starting_ids(), PREDICTION_TIME),
                _lineup(-900, -20, "4-2-3-1", list(range(-201, -212)), PREDICTION_TIME),
                models.OddsSnapshot(
                    fixture_id=-900,
                    league_id=-100,
                    season=2026,
                    bookmaker_id=-2,
                    bookmaker_name="Synthetic Book 2",
                    bet_id=-1,
                    bet_name="Match Winner",
                    odd_home=2.1,
                    odd_draw=3.4,
                    odd_away=3.8,
                    values_json=[],
                    fetched_at=datetime(2026, 5, 2, 10, tzinfo=UTC),
                    payload_json={"synthetic": True},
                ),
                models.Fixture(
                    fixture_id=-990,
                    league_id=-100,
                    season=2026,
                    date=datetime(2026, 5, 2, 13, tzinfo=UTC),
                    status="FT",
                    status_short="FT",
                    status_long="Synthetic future finished",
                    home_team_id=-10,
                    away_team_id=-30,
                    home_team="Synthetic Home",
                    away_team="Synthetic Opponent A",
                    home_goals=0,
                    away_goals=0,
                    payload_json={"synthetic": True, "future_league_draw": True},
                ),
            ]
        )
        result = build_feature_snapshot(session, -900, PREDICTION_TIME, feature_version="v3.0")

    features = result.features_json
    quality = result.data_quality_json
    assert result.snapshot.feature_version == "v3.0"
    assert features["official_lineup_available_flag"] == 1
    assert features["has_official_lineup_home"] is True
    assert features["has_official_lineup_away"] is True
    assert features["has_odds_multi_snapshot"] == 1
    assert "draw_risk_score" in features
    assert "draw_risk_league_draw_rate" in features
    assert features["draw_risk_league_draw_rate"] == 0.25
    assert features["ndw_odds_home_prob"] is not None
    assert features["ndw_odds_away_prob"] is not None
    assert features["ndw_odds_home_prob"] < 0.75
    assert 0 <= features["data_quality_score"] <= 100
    assert quality["has_official_lineup_home"] is True
    assert quality["has_official_lineup_away"] is True
    assert quality["official_lineup_available_flag"] is True
    assert quality["has_odds_multi_snapshot"] is True
    assert quality["v3_feature_version"] == "v3.0"


def test_ou_feature_builder_ignores_future_ou_odds_for_publication_quality(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_feature_builder_quality.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        session.add_all(
            [
                models.OddsSnapshot(
                    fixture_id=-900,
                    league_id=-100,
                    season=2026,
                    bookmaker_id=-3,
                    bookmaker_name="Synthetic O/U Book",
                    bet_id=-25,
                    bet_name="Over/Under 2.5",
                    odd_home=1.9,
                    odd_away=1.95,
                    values_json=[],
                    fetched_at=datetime(2026, 5, 2, 11, tzinfo=UTC),
                    payload_json={"synthetic": True},
                ),
                models.OddsSnapshot(
                    fixture_id=-900,
                    league_id=-100,
                    season=2026,
                    bookmaker_id=-3,
                    bookmaker_name="Synthetic O/U Book",
                    bet_id=-25,
                    bet_name="Over/Under 2.5",
                    odd_home=1.01,
                    odd_away=99.0,
                    values_json=[],
                    fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                    payload_json={"synthetic": True},
                ),
            ]
        )
        result = build_ou_feature_snapshot(session, -900, PREDICTION_TIME, ou_bet_id=-25)

    quality = result.data_quality_json
    assert quality["data_quality_version"] == "dq_v2"
    assert quality["source_quality_json"]["ou_odds"]["latest_fetched_at"] == (
        "2026-05-02T11:00:00+00:00"
    )
    assert quality["source_quality_json"]["ou_odds"]["fresh"] is True
    assert "future_snapshot_ignored" not in quality["source_quality_json"]["ou_odds"]["warnings"]
    assert result.features_json["publication_data_quality_score"] == (
        quality["publication_data_quality_score"]
    )


def test_ou_feature_builder_excludes_target_result_and_strips_leakage_fields(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_feature_target_result.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        _seed_point_in_time_sources(session)
        session.flush()
        target = session.get(models.Fixture, -900)
        target.date = datetime(2026, 4, 30, 19, tzinfo=UTC)
        target.status = "FT"
        target.status_short = "FT"
        target.home_goals = 9
        target.away_goals = 9

        result = build_ou_feature_snapshot(session, -900, PREDICTION_TIME, ou_bet_id=-25)

    features = result.features_json
    assert features["home_team_global_total_goals_avg_last3"] == 3.0
    for leakage_key in ("home_goals", "away_goals", "target_ou25", "total_goals"):
        assert leakage_key not in features


def test_ou_h2h_features_exclude_target_fixture_and_future_fixtures(tmp_path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_h2h_leakage.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        _seed_base(session)
        session.flush()
        target = session.get(models.Fixture, -900)
        target.date = datetime(2026, 4, 30, 19, tzinfo=UTC)
        target.status = "FT"
        target.status_short = "FT"
        target.home_goals = 9
        target.away_goals = 9
        session.add_all(
            [
                models.Fixture(
                    fixture_id=-950,
                    league_id=-100,
                    season=2026,
                    date=datetime(2026, 4, 10, 19, tzinfo=UTC),
                    status="FT",
                    status_short="FT",
                    status_long="Synthetic historical H2H",
                    home_team_id=-10,
                    away_team_id=-20,
                    home_team="Synthetic Home",
                    away_team="Synthetic Away",
                    home_goals=2,
                    away_goals=1,
                    payload_json={"synthetic": True},
                ),
                models.Fixture(
                    fixture_id=-951,
                    league_id=-100,
                    season=2026,
                    date=datetime(2026, 5, 3, 19, tzinfo=UTC),
                    status="FT",
                    status_short="FT",
                    status_long="Synthetic future H2H",
                    home_team_id=-20,
                    away_team_id=-10,
                    home_team="Synthetic Away",
                    away_team="Synthetic Home",
                    home_goals=0,
                    away_goals=0,
                    payload_json={"synthetic": True},
                ),
            ]
        )
        session.flush()

        features = build_h2h_features(
            session,
            -10,
            -20,
            PREDICTION_TIME,
            league_id=-100,
            exclude_fixture_id=-900,
        )

    assert features["h2h_matches_available"] == 1
    assert features["h2h_total_goals_avg_last3"] == 3.0
    assert features["h2h_total_goals_avg_last5"] == 3.0
    assert features["h2h_over25_rate_last5"] == 1.0


def _seed_point_in_time_sources(session) -> None:
    session.add_all(
        [
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-10,
                rank=2,
                points=40,
                goals_diff=12,
                all_played=20,
                snapshot_date=datetime(2026, 5, 2, 8, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 2, 8, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-10,
                rank=1,
                points=99,
                goals_diff=99,
                all_played=20,
                snapshot_date=datetime(2026, 5, 2, 13, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.StandingSnapshot(
                league_id=-100,
                season=2026,
                team_id=-20,
                rank=5,
                points=30,
                goals_diff=3,
                all_played=20,
                snapshot_date=datetime(2026, 5, 2, 8, tzinfo=UTC),
                fetched_at=datetime(2026, 5, 2, 8, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-1,
                bookmaker_name="Synthetic Book",
                bet_id=-1,
                bet_name="Match Winner",
                odd_home=2.0,
                odd_draw=3.5,
                odd_away=4.0,
                values_json=[],
                fetched_at=datetime(2026, 5, 2, 9, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.OddsSnapshot(
                fixture_id=-900,
                league_id=-100,
                season=2026,
                bookmaker_id=-1,
                bookmaker_name="Synthetic Book",
                bet_id=-1,
                bet_name="Match Winner",
                odd_home=1.01,
                odd_draw=20.0,
                odd_away=30.0,
                values_json=[],
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.ApiPredictionSnapshot(
                fixture_id=-900,
                winner_team_id=-10,
                win_or_draw=True,
                percent_home=45,
                percent_draw=30,
                percent_away=25,
                advice="Synthetic before cutoff",
                fetched_at=datetime(2026, 5, 2, 9, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
            models.ApiPredictionSnapshot(
                fixture_id=-900,
                winner_team_id=-20,
                win_or_draw=False,
                percent_home=99,
                percent_draw=0,
                percent_away=1,
                advice="Synthetic future leak",
                fetched_at=datetime(2026, 5, 2, 13, tzinfo=UTC),
                payload_json={"synthetic": True},
            ),
        ]
    )
