from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.config import DiscordWebhookRouteConfig, DiscordWebhooksConfig
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.ou_model.prediction.ou_run_daily import run_daily_ou_predictions
from football_predictor.ou_model.prediction.ou_service import OUPredictionOutput

NOW = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
TARGET_DATE = date(2026, 5, 2)


class FakeOUService:
    def __init__(
        self,
        session,
        *,
        confidence_label: str = "Very High",
        confidence_score: float = 88.0,
        publication_decision: str | None = "public",
        value_side: str | None = "OVER",
        no_bet_reason: str | None = None,
        non_publication_reason: str | None = None,
    ) -> None:
        self.session = session
        self.confidence_label = confidence_label
        self.confidence_score = confidence_score
        self.publication_decision = publication_decision
        self.value_side = value_side
        self.no_bet_reason = no_bet_reason
        self.non_publication_reason = non_publication_reason
        self.calls: list[int] = []

    def predict_fixture_ou(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        save_to_db: bool = True,
    ) -> OUPredictionOutput:
        self.calls.append(fixture_id)
        cutoff = prediction_time or NOW
        prediction_id = None
        if save_to_db:
            snapshot = models.OUFeatureSnapshot(
                fixture_id=fixture_id,
                prediction_time=cutoff,
                feature_version="synthetic-ou",
                threshold=2.5,
                features_json={"synthetic": True},
                data_quality_json={"overall_data_quality_score": 65},
            )
            self.session.add(snapshot)
            self.session.flush()
            record = models.OUModelPrediction(
                fixture_id=fixture_id,
                ou_feature_snapshot_id=snapshot.id,
                prediction_time=cutoff,
                model_version="synthetic-ou",
                threshold=2.5,
                p_over=0.72,
                p_under=0.28,
                confidence_score=self.confidence_score,
                confidence_label=self.confidence_label,
                expert_probabilities_json={},
                data_quality_json={"overall_data_quality_score": 65},
                payload_json={},
            )
            self.session.add(record)
            self.session.flush()
            prediction_id = record.id
        return OUPredictionOutput(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            model_version="synthetic-ou",
            threshold=2.5,
            p_over=0.72,
            p_under=0.28,
            xg_home=None,
            xg_away=None,
            xg_total=None,
            market_p_over=0.55,
            market_p_under=0.45,
            market_odd_over=1.9,
            market_odd_under=1.9,
            edge_over=0.17,
            edge_under=-0.17,
            ev_over=0.36,
            ev_under=-0.47,
            forecast_side="OVER",
            forecast_probability=0.72,
            value_side=self.value_side,
            value_probability=0.72 if self.value_side == "OVER" else 0.28,
            value_market_probability=0.55 if self.value_side == "OVER" else 0.45,
            value_market_odd=1.9,
            value_edge=0.17 if self.value_side == "OVER" else -0.17,
            value_ev=0.36 if self.value_side == "OVER" else -0.47,
            no_bet_reason=self.no_bet_reason,
            non_publication_reason=self.non_publication_reason,
            confidence_score_v2=self.confidence_score,
            confidence_label_v2=self.confidence_label,
            publication_decision=self.publication_decision,
            decision_version="ou_decision_v2",
            confidence_score=self.confidence_score,
            confidence_label=self.confidence_label,
            kickoff_time=cutoff,
            match_label="Synthetic Home vs Synthetic Away",
            competition="Synthetic League",
            expert_probabilities={"synthetic": 0.72},
            data_quality_json={"overall_data_quality_score": 65},
            ou_model_prediction_id=prediction_id,
        )


def test_daily_ou_late_window_sends_high_confidence_prediction(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_high.db'}")
    session_factory = create_session_factory(engine)
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        service = FakeOUService(session, confidence_label="Very High", confidence_score=88.0)
        summary = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=service,  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            window="late",
            now=NOW,
        )
        message = session.scalar(select(models.DiscordMessage))

    assert service.calls == [-501]
    assert summary.total == 1
    assert summary.sent == 1
    assert calls == 1
    assert message is not None
    assert message.message_type == "ou_prediction"
    assert message.channel_key == "predictions"
    assert message.model_prediction_id is None
    assert message.payload_json["model_family"] == "ou25"
    assert message.payload_json["ou_model_prediction_id"] is not None
    assert message.payload_json["daily_window"] == "late"


def test_daily_ou_medium_confidence_goes_to_staff_not_public(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_medium.db'}")
    session_factory = create_session_factory(engine)
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        service = FakeOUService(
            session,
            confidence_label="Medium",
            confidence_score=52.0,
            publication_decision="staff",
            non_publication_reason="confidence_insufficient",
        )
        summary = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=service,  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                webhooks_config=_staff_webhooks_config(),
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            window="late",
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        predictions = list(session.execute(select(models.OUModelPrediction)).scalars())

    assert summary.confidence_skipped == 1
    assert summary.sent == 0
    assert summary.results[0].status == "confidence_skipped"
    assert summary.results[0].reason == "confidence_insufficient"
    assert calls == ["https://example.invalid/staff"]
    assert len(messages) == 1
    assert messages[0].message_type == "ou_prediction_skipped"
    assert messages[0].channel_key == "predictions_staff"
    assert messages[0].status == "sent"
    assert messages[0].payload_json["model_family"] == "ou25"
    assert messages[0].payload_json["skip_reason"] == "confidence_insufficient"
    assert len(predictions) == 1


def test_daily_ou_no_bet_goes_to_staff_not_public(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_no_bet.db'}")
    session_factory = create_session_factory(engine)
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        service = FakeOUService(
            session,
            confidence_label="Uncertain",
            confidence_score=0.0,
            publication_decision="no_bet",
            value_side=None,
            no_bet_reason="ev_below_threshold",
        )
        summary = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=service,  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                webhooks_config=_staff_webhooks_config(),
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            window="late",
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())

    assert summary.success == 1
    assert summary.sent == 0
    assert summary.results[0].status == "no_bet"
    assert summary.results[0].reason == "ev_below_threshold"
    assert summary.results[0].publication_decision == "no_bet"
    assert calls == 1
    assert len(messages) == 1
    assert messages[0].message_type == "ou_prediction_skipped"
    assert messages[0].channel_key == "predictions_staff"
    assert messages[0].payload_json["skip_reason"] == "ev_below_threshold"


def _staff_webhooks_config() -> DiscordWebhooksConfig:
    return DiscordWebhooksConfig(
        routes=[
            DiscordWebhookRouteConfig(
                competition_key="global",
                channel_key="predictions_staff",
                webhook_url="https://example.invalid/staff",
            )
        ]
    )


def _seed_ou_fixtures(session: Any) -> None:
    session.add_all(
        [
            models.Team(team_id=-510, name="Synthetic Home", payload_json={"synthetic": True}),
            models.Team(team_id=-520, name="Synthetic Away", payload_json={"synthetic": True}),
            models.Fixture(
                fixture_id=-501,
                date=datetime(2026, 5, 2, 10, 20, tzinfo=UTC),
                league_id=-100,
                season=2026,
                status="NS",
                status_short="NS",
                home_team_id=-510,
                away_team_id=-520,
                home_team="Synthetic Home",
                away_team="Synthetic Away",
                payload_json={"synthetic": True},
            ),
            models.Fixture(
                fixture_id=-502,
                date=datetime(2026, 5, 2, 11, 0, tzinfo=UTC),
                league_id=-100,
                season=2026,
                status="NS",
                status_short="NS",
                home_team_id=-510,
                away_team_id=-520,
                home_team="Synthetic Home 2",
                away_team="Synthetic Away 2",
                payload_json={"synthetic": True},
            ),
        ]
    )
