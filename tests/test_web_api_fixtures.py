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
    today_kickoff = datetime.combine(today_local, datetime.min.time(), tzinfo=paris).replace(
        hour=21
    )
    tomorrow_kickoff = today_kickoff + timedelta(days=1)
    later_kickoff = today_kickoff + timedelta(days=9)

    session.add_all([
        models.League(
            league_id=1,
            season=2026,
            name="FIFA World Cup",
            country="World",
            type="Cup",
            category="international",
            logo="https://example.invalid/world-cup.png",
            payload_json={"secret": "must_not_leak"},
        ),
        models.League(
            league_id=61,
            season=2026,
            name="Ligue 1",
            country="France",
            type="League",
            category="domestic",
            payload_json={"payload_json": "must_not_leak"},
        ),
        models.TeamSeason(
            team_id=1,
            league_id=1,
            season=2026,
            competition_key="fifa_world_cup_2026",
            payload_json={"raw": True},
        ),
        models.TeamSeason(
            team_id=10,
            league_id=61,
            season=2026,
            competition_key="ligue1",
            payload_json={"raw": True},
        ),
        models.Team(team_id=1, name="Mexico"),
        models.Team(team_id=2, name="South Africa"),
        models.Team(team_id=3, name="Canada"),
        models.Team(team_id=4, name="Switzerland"),
        models.Team(team_id=10, name="Paris"),
        models.Team(team_id=11, name="Lyon"),
    ])
    session.add_all([
        models.Fixture(
            fixture_id=1001,
            date=today_kickoff.astimezone(UTC),
            timestamp=int(today_kickoff.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            venue_name="Estadio Azteca",
            venue_city="Mexico City",
            status="Not Started",
            status_long="Not Started",
            status_short="NS",
            home_team_id=1,
            away_team_id=2,
            home_team="Mexico",
            away_team="South Africa",
            payload_json={"payload_json": "must_not_leak", "data_quality_score": 12},
        ),
        models.Fixture(
            fixture_id=1002,
            date=tomorrow_kickoff.astimezone(UTC),
            timestamp=int(tomorrow_kickoff.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="Not Started",
            status_long="Not Started",
            status_short="NS",
            home_team_id=3,
            away_team_id=4,
            home_team="Canada",
            away_team="Switzerland",
            payload_json={"secret": "must_not_leak"},
        ),
        models.Fixture(
            fixture_id=2001,
            date=later_kickoff.astimezone(UTC),
            timestamp=int(later_kickoff.timestamp()),
            timezone="UTC",
            round="Regular Season - 1",
            league_id=61,
            season=2026,
            status="Not Started",
            status_long="Not Started",
            status_short="NS",
            home_team_id=10,
            away_team_id=11,
            home_team="Paris",
            away_team="Lyon",
            payload_json={"secret": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.ModelPrediction(
            id=1,
            fixture_id=1001,
            feature_snapshot_id=1,
            prediction_time=today_kickoff.astimezone(UTC) - timedelta(hours=4),
            model_version="v3",
            p_home=0.51,
            p_draw=0.24,
            p_away=0.25,
            predicted_result="HOME",
            confidence=0.6,
            confidence_label="Medium",
            confidence_score=64.0,
            data_quality_json={"score": 77},
            payload_json={"webhook": "must_not_leak"},
        ),
        models.OUModelPrediction(
            id=2,
            fixture_id=1001,
            ou_feature_snapshot_id=2,
            prediction_time=today_kickoff.astimezone(UTC) - timedelta(hours=3),
            model_version="ou-v2",
            threshold=2.5,
            p_over=0.55,
            p_under=0.45,
            data_quality_json={"score": 73},
            payload_json={"secret": "must_not_leak"},
        ),
        models.ComboTicket(
            id=3,
            ticket_key="ticket-1",
            status="LOCKED",
            competition_key="fifa_world_cup_2026",
            league_id=1,
            season=2026,
            combo_date=today_local,
            session_key="session-1",
            first_kickoff_at=today_kickoff.astimezone(UTC),
            last_kickoff_at=today_kickoff.astimezone(UTC),
            lock_time=today_kickoff.astimezone(UTC) - timedelta(minutes=20),
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
            payload_json={"route_json": "must_not_leak"},
        ),
        models.ComboTicketLeg(
            ticket_id=3,
            fixture_id=1001,
            leg_order=1,
            kickoff_at_utc=today_kickoff.astimezone(UTC),
            market_type="1X2",
            market_scope="FT_90",
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
            payload_json={"raw_snapshot": "must_not_leak"},
        ),
    ])
    session.commit()
    session.close()


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_list_competitions_ok(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/competitions", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    keys = {item["competition_key"] for item in payload}
    assert "fifa_world_cup_2026" in keys
    assert "ligue1" in keys
    assert "payload_json" not in response.text
    assert "must_not_leak" not in response.text


def test_get_competition_ok(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/competitions/fifa_world_cup_2026", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["league_id"] == 1
    assert payload["season"] == 2026
    assert payload["enabled"] is True
    assert payload["type"] == "Cup"


def test_get_unknown_competition_404(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/competitions/unknown", headers=_auth())

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "competition_not_found"


def test_fixtures_today_ok(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/fixtures/today?competition_key=fifa_world_cup_2026",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["fixture_id"] for item in payload] == [1001]
    fixture = payload[0]
    assert fixture["has_1x2_prediction"] is True
    assert fixture["has_ou_prediction"] is True
    assert fixture["has_combo"] is True
    assert fixture["latest_prediction_time"] is not None
    assert fixture["data_quality_score"] == 77.0
    assert "payload_json" not in response.text
    assert "must_not_leak" not in response.text


def test_fixtures_upcoming_limit_days_and_status(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/fixtures/upcoming?days=2&limit=1&status=NS&competition_key=fifa_world_cup_2026",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["competition_key"] == "fifa_world_cup_2026"

    invalid = api_client.get("/api/v1/fixtures/upcoming?days=31", headers=_auth())
    assert invalid.status_code == 422


def test_fixture_detail_ok(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/fixtures/1001", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["fixture_id"] == 1001
    assert payload["home_team"]["name"] == "Mexico"
    assert payload["away_team"]["name"] == "South Africa"
    assert payload["kickoff_at_paris"] is not None
    assert "payload_json" not in response.text


def test_unknown_fixture_404(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/fixtures/999999", headers=_auth())

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "fixture_not_found"


def test_auth_required_for_new_routes(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/competitions")

    assert response.status_code == 401


def test_api_disabled_for_new_routes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "false")
    monkeypatch.setenv("FOOTLUMEN_API_TOKEN", TOKEN)
    get_settings.cache_clear()
    dependencies._engine_for_url.cache_clear()
    client = TestClient(create_app())

    response = client.get("/api/v1/fixtures/today", headers=_auth())

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "api_disabled"


def test_read_endpoints_do_not_write(api_client: TestClient) -> None:
    statements: list[str] = []

    @event.listens_for(api_client.app.state.test_engine, "before_cursor_execute")
    def _capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement.strip().split(None, 1)[0].upper())

    api_client.get("/api/v1/competitions", headers=_auth())
    api_client.get("/api/v1/fixtures/today", headers=_auth())
    api_client.get("/api/v1/fixtures/1001", headers=_auth())

    assert not {"INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE"} & set(statements)
