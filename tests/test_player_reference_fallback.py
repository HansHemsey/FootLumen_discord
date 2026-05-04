from __future__ import annotations

from datetime import UTC, datetime

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.features.xi_features import build_player_xi_features
from football_predictor.reference.loaders import load_players_reference


def test_player_xi_uses_players_reference_as_position_fallback(
    tmp_path,
    players_reference_sample_path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'reference_fallback.db'}")
    session_factory = create_session_factory(engine)
    players_reference = load_players_reference(players_reference_sample_path)

    with session_scope(session_factory) as session:
        session.add_all(
            [
                models.Team(team_id=77, name="Angers", payload_json={}),
                models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}),
                models.Fixture(
                    fixture_id=-900,
                    date=datetime(2026, 5, 3, 19, tzinfo=UTC),
                    timezone="UTC",
                    round="Synthetic Round",
                    league_id=61,
                    season=2025,
                    status="NS",
                    status_short="NS",
                    home_team_id=77,
                    away_team_id=-20,
                    home_team="Angers",
                    away_team="Synthetic Away",
                    payload_json={"synthetic": True},
                ),
            ]
        )

        result = build_player_xi_features(
            session,
            -900,
            datetime(2026, 5, 2, 12, tzinfo=UTC),
            players_reference=players_reference,
        )

    home_xi = result.features_json["home_team_expected_xi_json"]
    assert {row["player_id"] for row in home_xi} == {455243, 191289}
    assert {row["position_group"] for row in home_xi} == {"ATT"}
    assert result.data_quality_json["home_team_reference_fallback_used"] is True
    assert result.data_quality_json["home_team_players_with_reference_position"] == 2
