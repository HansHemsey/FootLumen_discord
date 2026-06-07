from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.session import create_db_engine, create_session_factory, init_db
from football_predictor.web_api import dependencies
from football_predictor.web_api.app import create_app

TOKEN = "dev-token"


@pytest.fixture()
def api_client(monkeypatch, tmp_path) -> Iterator[TestClient]:
    database_url = f"sqlite:///{tmp_path / 'api.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "true")
    monkeypatch.setenv("FOOTLUMEN_API_READ_ONLY", "true")
    monkeypatch.setenv("FOOTLUMEN_API_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("FOOTLUMEN_API_TOKEN", TOKEN)
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Paris")
    get_settings.cache_clear()
    dependencies._engine_for_url.cache_clear()

    engine = create_db_engine(database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)
    _seed_database(session_factory())

    app = create_app()
    app.state.test_engine = engine
    with TestClient(app) as client:
        yield client


def _seed_database(session) -> None:
    paris = ZoneInfo("Europe/Paris")
    today_local = datetime.now(paris).date()
    now_utc = datetime.now(UTC)
    kickoff_today = datetime.combine(today_local, datetime.min.time(), tzinfo=paris).replace(
        hour=21
    ).astimezone(UTC)
    finished_at = now_utc - timedelta(days=1)

    session.add_all([
        models.League(
            league_id=1,
            season=2026,
            name="FIFA World Cup",
            country="World",
            type="Cup",
            category="international",
            payload_json={"secret": "must_not_leak"},
        ),
        models.TeamSeason(
            team_id=1,
            league_id=1,
            season=2026,
            competition_key="fifa_world_cup_2026",
            payload_json={"raw": True},
        ),
        models.Team(team_id=1, name="Mexico"),
        models.Team(team_id=2, name="South Africa"),
        models.Team(team_id=3, name="Canada"),
        models.Team(team_id=4, name="Switzerland"),
    ])
    session.add_all([
        models.Fixture(
            fixture_id=3001,
            date=kickoff_today,
            timestamp=int(kickoff_today.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="Not Started",
            status_long="Not Started",
            status_short="NS",
            home_team_id=1,
            away_team_id=2,
            home_team="Mexico",
            away_team="South Africa",
            payload_json={"payload_json": "must_not_leak"},
        ),
        models.Fixture(
            fixture_id=3002,
            date=finished_at,
            timestamp=int(finished_at.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="Match Finished",
            status_long="Match Finished",
            status_short="FT",
            home_team_id=3,
            away_team_id=4,
            home_team="Canada",
            away_team="Switzerland",
            home_goals=2,
            away_goals=1,
            payload_json={"raw_snapshot": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.ModelPrediction(
            id=401,
            fixture_id=3002,
            feature_snapshot_id=100,
            prediction_time=finished_at - timedelta(hours=3),
            model_version="v3",
            p_home=0.51,
            p_draw=0.24,
            p_away=0.25,
            predicted_result="HOME",
            confidence_label="Medium",
            confidence_score=64.0,
            data_quality_json={"score": 77},
            payload_json={"publication_decision": "public", "secret": "must_not_leak"},
        ),
        models.OUModelPrediction(
            id=402,
            fixture_id=3002,
            ou_feature_snapshot_id=101,
            prediction_time=finished_at - timedelta(hours=2),
            model_version="ou-v2",
            threshold=2.5,
            p_over=0.57,
            p_under=0.43,
            forecast_side="OVER",
            forecast_probability=0.57,
            value_side="OVER",
            p_pick=0.57,
            edge_pick=0.04,
            ev_pick=0.06,
            confidence_score_v2=68.0,
            confidence_label_v2="Medium",
            publication_decision="public",
            data_quality_json={"score": 75},
            payload_json={"payload_json": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.ComboTicket(
            id=501,
            ticket_key="public-ticket",
            status="PUBLIC_PUBLISHED",
            competition_key="fifa_world_cup_2026",
            league_id=1,
            season=2026,
            combo_date=today_local,
            session_key="session-public",
            first_kickoff_at=kickoff_today,
            last_kickoff_at=kickoff_today,
            lock_time=kickoff_today - timedelta(minutes=20),
            legs_count=1,
            combined_decimal_odds=2.0,
            combined_probability_raw=0.5,
            combined_probability_adjusted=0.48,
            combined_fair_odds=2.08,
            combined_ev_raw=0.04,
            combined_ev_adjusted=0.02,
            combined_confidence_score=63,
            combined_confidence_label="Medium",
            post_lock_risk_score=0.1,
            freshness_score=0.9,
            lineup_risk_score=0.1,
            publication_decision="PUBLIC_PUBLISHED",
            warnings_json=["odds_missing", "staff_internal"],
            payload_json={
                "route_json": "must_not_leak",
                "settlement": {
                    "status": "WON",
                    "settlement_status": "WON",
                    "leg_results": ["WON"],
                    "profit_unit": 1.0,
                    "settled_at": now_utc.isoformat(),
                    "settlement_warning": "manual_review_required",
                    "manual_review_required": True,
                },
            },
        ),
        models.ComboTicket(
            id=502,
            ticket_key="staff-ticket",
            status="STAFF_ONLY",
            competition_key="fifa_world_cup_2026",
            league_id=1,
            season=2026,
            combo_date=today_local,
            session_key="session-staff",
            first_kickoff_at=kickoff_today,
            last_kickoff_at=kickoff_today,
            lock_time=kickoff_today - timedelta(minutes=20),
            legs_count=1,
            combined_decimal_odds=2.0,
            combined_probability_raw=0.5,
            combined_probability_adjusted=0.48,
            combined_fair_odds=2.08,
            combined_ev_raw=0.04,
            combined_ev_adjusted=0.02,
            combined_confidence_score=63,
            combined_confidence_label="Medium",
            post_lock_risk_score=0.1,
            freshness_score=0.9,
            lineup_risk_score=0.1,
            publication_decision="STAFF_ONLY",
            payload_json={"webhook": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.ComboTicketLeg(
            ticket_id=501,
            fixture_id=3001,
            leg_order=1,
            kickoff_at_utc=kickoff_today,
            market_type="HOME",
            market_scope="NINETY_MIN",
            selection="Mexico",
            decimal_odd=2.0,
            model_probability=0.51,
            market_probability=0.48,
            edge=0.03,
            ev=0.04,
            confidence_score=63,
            confidence_label="Medium",
            data_quality_score=77,
            lineup_status="unknown",
            payload_json={"match_label": "Mexico vs South Africa", "raw_snapshot": "must_not_leak"},
        ),
        models.ComboTicketLeg(
            ticket_id=502,
            fixture_id=3001,
            leg_order=1,
            kickoff_at_utc=kickoff_today,
            market_type="HOME",
            market_scope="NINETY_MIN",
            selection="Mexico",
            decimal_odd=2.0,
            model_probability=0.51,
            market_probability=0.48,
            edge=0.03,
            ev=0.04,
            confidence_score=63,
            confidence_label="Medium",
            data_quality_score=77,
            lineup_status="unknown",
        ),
        models.ComboTicketLeg(
            ticket_id=501,
            fixture_id=3002,
            leg_order=2,
            kickoff_at_utc=finished_at,
            market_type="HOME",
            market_scope="NINETY_MIN",
            selection="Canada",
            decimal_odd=1.8,
            model_probability=0.56,
            market_probability=0.52,
            edge=0.04,
            ev=0.06,
            confidence_score=62,
            confidence_label="Medium",
            data_quality_score=76,
            lineup_status="confirmed",
        ),
    ])
    session.add(
        models.DiscordMessage(
            fixture_id=3002,
            model_prediction_id=401,
            status="sent",
            competition_key="fifa_world_cup_2026",
            league_id=1,
            season=2026,
            channel_key="predictions",
            message_type="prediction",
            dry_run=False,
            print_only=False,
            message_markdown="public prediction",
            payload_json={"secret": "must_not_leak"},
        )
    )
    session.commit()
    session.close()


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_combos_today_filters_staff_by_default(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/combos/today?limit=10", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["limit"] == 10
    assert [item["ticket_key"] for item in payload["items"]] == ["public-ticket"]
    assert payload["items"][0]["warnings_public"][0]["message"] == "Cotes indisponibles"
    assert "staff_internal" not in response.text
    assert "payload_json" not in response.text
    assert "must_not_leak" not in response.text


def test_combos_today_include_staff(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/combos/today?include_staff=true", headers=_auth())

    assert response.status_code == 200
    keys = {item["ticket_key"] for item in response.json()["items"]}
    assert keys == {"public-ticket", "staff-ticket"}


def test_combo_detail_ok_and_unknown_404(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/combos/public-ticket", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket_key"] == "public-ticket"
    assert payload["settlement"]["status"] == "WON"
    assert payload["settlement"]["manual_review_required"] is True
    assert payload["legs"][0]["match_label"] == "Mexico vs South Africa"
    assert "route_json" not in response.text

    missing = api_client.get("/api/v1/combos/unknown", headers=_auth())
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "combo_not_found"


def test_latest_combos_and_limits(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/combos/latest?include_staff=true&limit=2", headers=_auth())

    assert response.status_code == 200
    assert response.json()["meta"]["limit"] == 2
    assert len(response.json()["items"]) == 2
    too_large = api_client.get("/api/v1/combos/latest?limit=51", headers=_auth())
    assert too_large.status_code == 422


def test_results_recent_ok(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/results/recent?competition_key=fifa_world_cup_2026&days=7&limit=10",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["fixture"]["fixture_id"] == 3002
    assert payload["items"][0]["home_goals"] == 2
    assert payload["items"][0]["result_1x2"] == "HOME"
    assert payload["items"][0]["prediction_1x2"]["correct"] is True
    assert payload["items"][0]["ou_result"] == "OVER"
    assert payload["items"][0]["ou_prediction"]["pick_result"] == "WON"
    assert payload["items"][0]["combo_ticket_count"] == 1
    assert "payload_json" not in response.text
    assert "must_not_leak" not in response.text


def test_performance_summary_ok(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/performance/summary?competition_key=fifa_world_cup_2026&days=7",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_predictions"] >= 1
    assert payload["total_ou_predictions"] == 1
    assert payload["total_combos"] == 2
    assert payload["total_public_predictions"] == 1
    assert payload["roi"] is None
    assert payload["by_market"][0]["market"] == "1X2"
    assert "payload_json" not in response.text
    assert "must_not_leak" not in response.text


def test_auth_required(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/combos/latest")

    assert response.status_code == 401


def test_endpoints_do_not_write_or_launch_settlement(api_client: TestClient, monkeypatch) -> None:
    from football_predictor.world_cup_combos.worldcup_combo_settlement import (
        WorldCupComboSettlementService,
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("settlement must not run")

    monkeypatch.setattr(WorldCupComboSettlementService, "settle_open_records", fail_if_called)
    writes: list[str] = []
    engine = api_client.app.state.test_engine

    def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        for path in (
            "/api/v1/combos/latest?include_staff=true",
            "/api/v1/combos/public-ticket",
            "/api/v1/results/recent?days=7",
            "/api/v1/performance/summary?days=7",
        ):
            response = api_client.get(path, headers=_auth())
            assert response.status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert writes == []
