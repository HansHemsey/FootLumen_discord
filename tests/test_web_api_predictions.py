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
def prediction_api_client(monkeypatch, tmp_path) -> Iterator[TestClient]:
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
    kickoff_1 = datetime(2026, 6, 11, 21, 0, tzinfo=paris).astimezone(UTC)
    kickoff_2 = datetime(2026, 6, 11, 23, 0, tzinfo=paris).astimezone(UTC)
    kickoff_3 = datetime(2026, 6, 12, 3, 0, tzinfo=paris).astimezone(UTC)

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
        ),
        models.Team(team_id=1, name="Mexico"),
        models.Team(team_id=2, name="South Africa"),
        models.Team(team_id=3, name="Canada"),
        models.Team(team_id=4, name="Switzerland"),
        models.Team(team_id=5, name="Brazil"),
        models.Team(team_id=6, name="Morocco"),
    ])
    session.add_all([
        models.Fixture(
            fixture_id=1101,
            date=kickoff_1,
            timestamp=int(kickoff_1.timestamp()),
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
            fixture_id=1102,
            date=kickoff_2,
            timestamp=int(kickoff_2.timestamp()),
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
            payload_json={"raw_snapshot": "must_not_leak"},
        ),
        models.Fixture(
            fixture_id=1103,
            date=kickoff_3,
            timestamp=int(kickoff_3.timestamp()),
            timezone="UTC",
            round="Group Stage - 1",
            league_id=1,
            season=2026,
            status="Not Started",
            status_long="Not Started",
            status_short="NS",
            home_team_id=5,
            away_team_id=6,
            home_team="Brazil",
            away_team="Morocco",
            payload_json={"secret": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.V3ModelPrediction(
            id=301,
            fixture_id=1101,
            v3_feature_snapshot_id=9001,
            prediction_time=kickoff_1 - timedelta(hours=3),
            model_version="v3-public",
            fusion_strategy="stacked",
            p_v3_final_home=0.52,
            p_v3_final_draw=0.25,
            p_v3_final_away=0.23,
            data_quality_score=82.0,
            confidence_score=71.0,
            confidence_label="High",
            predicted_result="HOME",
            explanations_json=["Mexico has a value edge", {"debug": "staff only"}],
            data_quality_json={"warnings": ["odds_missing", "staff_internal"]},
            payload_json={
                "publication_decision": "public",
                "v3_feature_snapshot_id": 9001,
                "payload_json": {"raw": True},
                "webhook": "must_not_leak",
            },
        ),
        models.ModelPrediction(
            id=101,
            fixture_id=1101,
            feature_snapshot_id=7001,
            prediction_time=kickoff_1 - timedelta(hours=2),
            model_version="legacy-newer-but-not-preferred",
            p_home=0.1,
            p_draw=0.8,
            p_away=0.1,
            predicted_result="DRAW",
            confidence_label="Low",
            confidence_score=30.0,
            data_quality_json={"score": 20},
            payload_json={"publication_decision": "no_bet"},
        ),
        models.ModelPrediction(
            id=102,
            fixture_id=1102,
            feature_snapshot_id=7002,
            prediction_time=kickoff_2 - timedelta(hours=2),
            model_version="legacy-v2",
            p_home=0.42,
            p_draw=0.31,
            p_away=0.27,
            predicted_result="HOME",
            confidence_label="Medium",
            confidence_score=60.0,
            explanation_json=["Canada slight edge"],
            data_quality_json={"score": 66},
            payload_json={"publication_decision": "staff", "secret": "must_not_leak"},
        ),
    ])
    session.add_all([
        models.OUModelPrediction(
            id=201,
            fixture_id=1101,
            ou_feature_snapshot_id=8001,
            prediction_time=kickoff_1 - timedelta(hours=1),
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
            payload_json={"expert_probabilities_json": "must_not_leak"},
        ),
        models.OUModelPrediction(
            id=202,
            fixture_id=1102,
            ou_feature_snapshot_id=8002,
            prediction_time=kickoff_2 - timedelta(hours=1),
            model_version="ou-legacy",
            threshold=2.5,
            p_over=0.49,
            p_under=0.51,
            confidence_score=50.0,
            confidence_label="Low",
            publication_decision="no_bet",
            no_bet_reason="legacy_decision_version",
            data_quality_json={"score": 61},
            payload_json={"payload_json": "must_not_leak"},
        ),
    ])
    session.commit()
    session.close()


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_latest_1x2_returns_v3_preferred_and_latest_per_fixture(
    prediction_api_client: TestClient,
) -> None:
    response = prediction_api_client.get(
        "/api/v1/predictions/latest?competition_key=fifa_world_cup_2026&limit=10",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["limit"] == 10
    items = payload["items"]
    assert {item["fixture"]["fixture_id"] for item in items} == {1101, 1102}
    fixture_1101 = next(item for item in items if item["fixture"]["fixture_id"] == 1101)
    assert fixture_1101["model_version"] == "v3-public"
    assert fixture_1101["p_home"] == 0.52
    assert fixture_1101["publication_decision"] == "public"
    assert fixture_1101["warnings_public"][0]["message"] == "Cotes indisponibles"
    assert "payload_json" not in response.text
    assert "feature_snapshot" not in response.text
    assert "must_not_leak" not in response.text


def test_1x2_fixture_detail_ok(prediction_api_client: TestClient) -> None:
    response = prediction_api_client.get("/api/v1/predictions/1101", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["fixture"]["home_team"]["name"] == "Mexico"
    assert payload["model_version"] == "v3-public"
    assert payload["confidence_label"] == "High"
    assert "Mexico has a value edge" in payload["explanations_public"]


def test_1x2_absent_returns_404(prediction_api_client: TestClient) -> None:
    response = prediction_api_client.get("/api/v1/predictions/999999", headers=_auth())

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "prediction_not_found"


def test_latest_1x2_filters_date_limit_and_public(prediction_api_client: TestClient) -> None:
    response = prediction_api_client.get(
        "/api/v1/predictions/latest?date=2026-06-11&only_public=true&limit=1",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["fixture"]["fixture_id"] == 1101

    invalid = prediction_api_client.get("/api/v1/predictions/latest?limit=101", headers=_auth())
    assert invalid.status_code == 422


def test_latest_ou_returns_v2_and_legacy_does_not_break(
    prediction_api_client: TestClient,
) -> None:
    response = prediction_api_client.get(
        "/api/v1/ou/latest?competition_key=fifa_world_cup_2026&limit=10",
        headers=_auth(),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["fixture"]["fixture_id"] for item in items} == {1101, 1102}
    v2 = next(item for item in items if item["fixture"]["fixture_id"] == 1101)
    legacy = next(item for item in items if item["fixture"]["fixture_id"] == 1102)
    assert v2["model_version"] == "ou-v2"
    assert v2["value_side"] == "OVER"
    assert v2["confidence_score_v2"] == 68.0
    assert legacy["model_version"] == "ou-legacy"
    assert legacy["value_side"] is None
    assert "payload_json" not in response.text
    assert "expert_probabilities_json" not in response.text
    assert "must_not_leak" not in response.text


def test_ou_fixture_detail_ok(prediction_api_client: TestClient) -> None:
    response = prediction_api_client.get("/api/v1/ou/1101", headers=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_side"] == "OVER"
    assert payload["value_side"] == "OVER"
    assert payload["ev_pick"] == 0.06


def test_ou_absent_returns_404(prediction_api_client: TestClient) -> None:
    response = prediction_api_client.get("/api/v1/ou/999999", headers=_auth())

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ou_prediction_not_found"


def test_latest_ou_filters_value_picks_include_no_bet_and_limit(
    prediction_api_client: TestClient,
) -> None:
    response = prediction_api_client.get(
        "/api/v1/ou/latest?only_value_picks=true&include_no_bet=false&limit=1",
        headers=_auth(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["fixture"]["fixture_id"] == 1101

    invalid = prediction_api_client.get("/api/v1/ou/latest?limit=101", headers=_auth())
    assert invalid.status_code == 422


def test_auth_required_and_disabled_for_prediction_routes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "true")
    monkeypatch.setenv("FOOTLUMEN_API_REQUIRE_TOKEN", "true")
    monkeypatch.setenv("FOOTLUMEN_API_TOKEN", TOKEN)
    get_settings.cache_clear()
    dependencies._engine_for_url.cache_clear()
    client = TestClient(create_app())

    assert client.get("/api/v1/predictions/latest").status_code == 401

    monkeypatch.setenv("FOOTLUMEN_API_ENABLED", "false")
    get_settings.cache_clear()
    disabled_client = TestClient(create_app())
    response = disabled_client.get("/api/v1/ou/latest", headers=_auth())
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "api_disabled"


def test_prediction_endpoints_do_not_write(prediction_api_client: TestClient) -> None:
    statements: list[str] = []

    @event.listens_for(prediction_api_client.app.state.test_engine, "before_cursor_execute")
    def _capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement.strip().split(None, 1)[0].upper())

    prediction_api_client.get("/api/v1/predictions/latest", headers=_auth())
    prediction_api_client.get("/api/v1/predictions/1101", headers=_auth())
    prediction_api_client.get("/api/v1/ou/latest", headers=_auth())
    prediction_api_client.get("/api/v1/ou/1101", headers=_auth())

    assert not {"INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE"} & set(statements)
