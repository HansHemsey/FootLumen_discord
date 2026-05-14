from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.ou_model.prediction.ou_run_daily import run_daily_ou_predictions
from football_predictor.ou_model.prediction.ou_service import OUPredictionOutput
from football_predictor.utils.exceptions import PredictionError

NOW = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
TARGET_DATE = date(2026, 5, 2)


class FakeOUService:
    def __init__(
        self,
        session,
        *,
        confidence_label: str = "Very High",
        confidence_score: float = 88.0,
        data_quality_score: float = 65.0,
        model_version: str = "synthetic-ou",
    ) -> None:
        self.session = session
        self.confidence_label = confidence_label
        self.confidence_score = confidence_score
        self.data_quality_score = data_quality_score
        self.model_version = model_version
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
            feature_version = f"{self.model_version}-{self.confidence_score:.1f}"
            snapshot = models.OUFeatureSnapshot(
                fixture_id=fixture_id,
                prediction_time=cutoff,
                feature_version=feature_version,
                threshold=2.5,
                features_json={"synthetic": True},
                data_quality_json={"publication_data_quality_score": self.data_quality_score},
            )
            self.session.add(snapshot)
            self.session.flush()
            record = models.OUModelPrediction(
                fixture_id=fixture_id,
                ou_feature_snapshot_id=snapshot.id,
                prediction_time=cutoff,
                model_version=self.model_version,
                threshold=2.5,
                p_over=0.72,
                p_under=0.28,
                confidence_score=self.confidence_score,
                confidence_label=self.confidence_label,
                expert_probabilities_json={},
                data_quality_json={"publication_data_quality_score": self.data_quality_score},
                payload_json={},
            )
            self.session.add(record)
            self.session.flush()
            prediction_id = record.id
        return OUPredictionOutput(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            model_version=self.model_version,
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
            confidence_score=self.confidence_score,
            confidence_label=self.confidence_label,
            kickoff_time=cutoff,
            match_label="Synthetic Home vs Synthetic Away",
            competition="Synthetic League",
            expert_probabilities={"synthetic": 0.72},
            data_quality_json={"publication_data_quality_score": self.data_quality_score},
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
    model_dir = _write_approved_artifact(tmp_path / "approved-ou", "ou25")
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
            shadow_mode=False,
            model_dir=model_dir,
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
    assert message.payload_json["shadow_mode"] is False
    assert message.payload_json["publication_decision"]["allowed"] is True


def test_daily_ou_duplicate_dedupe_key_is_not_sent_twice(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_duplicate.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_approved_artifact(tmp_path / "approved-ou", "ou25")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        first_service = FakeOUService(session, confidence_score=88.0)
        first = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=first_service,  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )
        second_service = FakeOUService(session, confidence_score=89.0)
        second = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=second_service,  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )

    assert first.sent == 1
    assert second.sent == 0
    assert second.results[0].status == "duplicate_skipped"
    assert calls == 1


def test_daily_ou_different_model_version_can_send_again(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_model_versions.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_approved_artifact(tmp_path / "approved-ou", "ou25")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        first = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=FakeOUService(session, model_version="synthetic-ou-a"),  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )
        second = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=FakeOUService(session, model_version="synthetic-ou-b"),  # type: ignore[arg-type]
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/ou",
                http_client=http_client,
            ),
            send_discord=True,
            dry_run=False,
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )

    assert first.sent == 1
    assert second.sent == 1
    assert calls == 2


def test_daily_ou_production_refuses_without_approved_artifact(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_unapproved.db'}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_ou_fixtures(session)
        service = FakeOUService(session)
        with pytest.raises(PredictionError, match="approved backtest artifact"):
            run_daily_ou_predictions(
                TARGET_DATE,
                session=session,
                ou_service=service,  # type: ignore[arg-type]
                send_discord=False,
                shadow_mode=False,
                model_dir=tmp_path / "missing-ou-approval",
                window="late",
                now=NOW,
            )

    assert service.calls == []


def test_daily_ou_shadow_mode_allows_internal_run_without_approval(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_shadow.db'}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_ou_fixtures(session)
        service = FakeOUService(session)
        summary = run_daily_ou_predictions(
            TARGET_DATE,
            session=session,
            ou_service=service,  # type: ignore[arg-type]
            send_discord=False,
            model_dir=tmp_path / "missing-ou-approval",
            window="late",
            now=NOW,
        )

    assert summary.shadow_mode is True
    assert summary.success == 1
    assert service.calls == [-501]


def test_daily_ou_medium_confidence_is_not_published(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_medium.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_approved_artifact(tmp_path / "approved-ou", "ou25")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        service = FakeOUService(session, confidence_label="Medium", confidence_score=52.0)
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
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        predictions = list(session.execute(select(models.OUModelPrediction)).scalars())

    assert summary.confidence_skipped == 1
    assert summary.sent == 0
    assert summary.results[0].status == "confidence_skipped"
    assert summary.results[0].reason == "confidence_below_publish_threshold"
    assert calls == 0
    assert messages == []
    assert len(predictions) == 1
    assert predictions[0].payload_json["non_publication_reason"] == (
        "confidence_below_publish_threshold"
    )


def test_daily_ou_high_confidence_low_quality_is_not_published(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'ou_daily_low_quality.db'}")
    session_factory = create_session_factory(engine)
    model_dir = _write_approved_artifact(tmp_path / "approved-ou", "ou25")
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        _seed_ou_fixtures(session)
        service = FakeOUService(
            session,
            confidence_label="Very High",
            confidence_score=88.0,
            data_quality_score=59.0,
        )
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
            shadow_mode=False,
            model_dir=model_dir,
            window="late",
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        predictions = list(session.execute(select(models.OUModelPrediction)).scalars())

    assert summary.confidence_skipped == 1
    assert summary.sent == 0
    assert summary.results[0].status == "confidence_skipped"
    assert summary.results[0].reason == "data_quality_below_publish_threshold"
    assert calls == 0
    assert messages == []
    assert len(predictions) == 1
    assert predictions[0].payload_json["non_publication_reason"] == (
        "data_quality_below_publish_threshold"
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


def _write_approved_artifact(path: Path, model_family: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "confidence_thresholds.json").write_text(
        (
            '{"threshold_version":"confidence_thresholds_v1",'
            f'"model_family":"{model_family}",'
            '"production_approved":true,'
            '"thresholds":{"global":{"high":60.0,"very_high":80.0}}}'
        ),
        encoding="utf-8",
    )
    return path
