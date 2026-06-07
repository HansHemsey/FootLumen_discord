from __future__ import annotations

from contextlib import suppress
from datetime import UTC, date, datetime

from football_predictor.db import models
from football_predictor.web_api.dependencies import get_read_only_session
from football_predictor.web_api.schemas.combos import combo_ticket_from_model
from football_predictor.web_api.schemas.common import (
    public_explanations_from_json,
    public_warnings_from_json,
)
from football_predictor.web_api.schemas.ou import ou_prediction_from_model
from football_predictor.web_api.schemas.predictions import prediction_1x2_from_model


def _fixture() -> models.Fixture:
    return models.Fixture(
        fixture_id=1001,
        date=datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
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
        venue_name="Estadio Azteca",
        venue_city="Mexico City",
        payload_json={"payload_json": "must_not_leak"},
    )


def test_prediction_1x2_dto_filters_payload_and_staff_internals() -> None:
    prediction = models.ModelPrediction(
        id=501,
        fixture_id=1001,
        feature_snapshot_id=42,
        prediction_time=datetime(2026, 6, 11, 8, 0, tzinfo=UTC),
        model_version="v3",
        p_home=0.48,
        p_draw=0.27,
        p_away=0.25,
        predicted_result="HOME",
        confidence_score=66.0,
        confidence_label="Medium",
        explanation_json=["old explanation"],
        explanations_json=[
            {"message": "Home side has positive value"},
            {"debug": "staff only"},
            "Bearer " + "verysecretTOKENvalue1234567890",
        ],
        data_quality_json={"score": 74, "warnings": ["odds_missing", "staff_raw_snapshot_failed"]},
        payload_json={
            "publication_decision": "staff",
            "feature_snapshot_id": 42,
            "payload_json": {"raw": True},
            "webhook_url": "https://discord.com" + "/api/webhooks/123/abc",
        },
    )

    dto = prediction_1x2_from_model(prediction, _fixture())
    dumped = dto.model_dump_json()

    assert dto.prediction_id == 501
    assert dto.fixture.fixture_id == 1001
    assert dto.fixture.competition_key == "fifa_world_cup_2026"
    assert dto.publication_decision == "staff"
    assert dto.warnings_public[0].message == "Cotes indisponibles"
    assert "Home side has positive value" in dto.explanations_public
    assert "feature_snapshot_id" not in dumped
    assert "payload_json" not in dumped
    assert "discord.com" + "/api/webhooks" not in dumped
    assert "verysecretTOKEN" not in dumped
    assert "staff_raw_snapshot_failed" not in dumped


def test_ou_prediction_dto_filters_expert_payload() -> None:
    prediction = models.OUModelPrediction(
        id=701,
        fixture_id=1001,
        ou_feature_snapshot_id=12,
        prediction_time=datetime(2026, 6, 11, 8, 5, tzinfo=UTC),
        model_version="ou-v2",
        threshold=2.5,
        p_over=0.58,
        p_under=0.42,
        forecast_side="OVER",
        forecast_probability=0.58,
        value_side="UNDER",
        p_pick=0.42,
        edge_pick=0.04,
        ev_pick=0.05,
        confidence_score_v2=61.0,
        confidence_label_v2="Medium",
        publication_decision="staff",
        no_bet_reason=None,
        expert_probabilities_json={"raw_model": "hidden"},
        data_quality_json={"data_quality_score": 81},
        payload_json={"secret": "SHOULD_NOT_LEAK"},
    )

    dto = ou_prediction_from_model(prediction, _fixture())
    dumped = dto.model_dump_json()

    assert dto.value_side == "UNDER"
    assert dto.forecast_side == "OVER"
    assert dto.data_quality_score == 81.0
    assert "expert_probabilities_json" not in dumped
    assert "payload_json" not in dumped
    assert "SHOULD_NOT_LEAK" not in dumped


def test_combo_ticket_dto_filters_raw_payloads() -> None:
    ticket = models.ComboTicket(
        id=91,
        ticket_key="cdm-2026-abc",
        status="LOCKED",
        competition_key="fifa_world_cup_2026",
        league_id=1,
        season=2026,
        combo_date=date(2026, 6, 11),
        session_key="session-1",
        first_kickoff_at=datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
        last_kickoff_at=datetime(2026, 6, 12, 2, 0, tzinfo=UTC),
        lock_time=datetime(2026, 6, 11, 18, 40, tzinfo=UTC),
        legs_count=1,
        combined_decimal_odds=2.4,
        combined_probability_raw=0.46,
        combined_probability_adjusted=0.43,
        combined_fair_odds=2.33,
        combined_ev_raw=0.08,
        combined_ev_adjusted=0.04,
        combined_confidence_score=64.0,
        combined_confidence_label="Medium",
        post_lock_risk_score=0.2,
        freshness_score=0.9,
        lineup_risk_score=0.1,
        publication_decision="PUBLIC_PUBLISHED",
        no_publish_reason=None,
        warnings_json=["lineup_missing_close_to_kickoff", "staff_only_debug"],
        payload_json={"discord_route": "private", "webhook": "secret"},
    )
    leg = models.ComboTicketLeg(
        ticket_id=91,
        fixture_id=1001,
        leg_order=1,
        kickoff_at_utc=datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
        market_type="1X2",
        market_scope="FT_90",
        selection="Mexico win",
        decimal_odd=1.9,
        model_probability=0.56,
        market_probability=0.52,
        edge=0.04,
        ev=0.06,
        confidence_score=63.0,
        confidence_label="Medium",
        data_quality_score=78.0,
        lineup_status="partial",
        warnings_json=["odds_stale"],
        payload_json={
            "match_label": "Mexico vs South Africa",
            "bookmaker_name": "consensus",
            "executable_decimal_odd": 1.88,
            "raw_snapshot": {"secret": "hidden"},
        },
    )

    dto = combo_ticket_from_model(ticket, [leg])
    dumped = dto.model_dump_json()

    assert dto.ticket_key == "cdm-2026-abc"
    assert dto.legs[0].match_label == "Mexico vs South Africa"
    assert dto.legs[0].bookmaker_name == "consensus"
    assert dto.legs[0].warnings_public[0].message == "Cotes a rafraichir"
    assert dto.warnings_public[0].message == "Composition non confirmee"
    assert "payload_json" not in dumped
    assert "raw_snapshot" not in dumped
    assert "discord_route" not in dumped
    assert "webhook" not in dumped
    assert "staff_only_debug" not in dumped


def test_public_warning_filtering_translates_known_codes_only() -> None:
    warnings = public_warnings_from_json([
        "odds_missing",
        "internal_staff_traceback",
        {"code": "data_quality_below_threshold"},
    ])

    assert [warning.message for warning in warnings] == [
        "Cotes indisponibles",
        "Qualite des donnees insuffisante",
    ]


def test_public_explanations_sanitize_secrets() -> None:
    explanations = public_explanations_from_json([
        "Value positive",
        "Authorization: Bearer " + "abcdefghijklmnopqrstuvwxyz123456",
    ])

    joined = " ".join(explanations)
    assert "Value positive" in joined
    assert "abcdefghijklmnopqrstuvwxyz" not in joined


def test_read_only_session_dependency_never_commits(monkeypatch) -> None:
    from football_predictor.config.settings import get_settings
    from football_predictor.web_api import dependencies

    class FakeResult:
        def scalar_one(self) -> int:
            return 1

    class FakeSession:
        committed = False
        rolled_back = False
        closed = False

        def execute(self, _statement):
            return FakeResult()

        def commit(self) -> None:
            self.committed = True
            raise AssertionError("API read-only sessions must not commit")

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    get_settings.cache_clear()
    dependencies._engine_for_url.cache_clear()
    monkeypatch.setattr(dependencies, "create_db_engine", lambda _url: object())
    monkeypatch.setattr(
        dependencies,
        "create_session_factory",
        lambda _engine: lambda: fake_session,
    )

    generator = get_read_only_session()
    session = next(generator)
    assert session is fake_session
    with suppress(StopIteration):
        next(generator)

    assert fake_session.committed is False
    assert fake_session.rolled_back is True
    assert fake_session.closed is True
