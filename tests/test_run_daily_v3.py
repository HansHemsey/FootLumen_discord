from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from typer.testing import CliRunner

from football_predictor.cli import app
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.run_daily import run_daily_predictions_v3
from football_predictor.prediction.scheduler import DailyPredictionWindow
from football_predictor.prediction.v3_service import PredictionV3Output
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.exceptions import PredictionError

NOW = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
TARGET_DATE = date(2026, 5, 2)


class FakePredictionV3Service:
    def __init__(
        self,
        session,
        *,
        fail_fixture_ids: set[int] | None = None,
        confidence_label: str = "High",
        confidence_score: float = 72.0,
        data_quality_score: float = 61.0,
    ) -> None:
        self.session = session
        self.fail_fixture_ids = fail_fixture_ids or set()
        self.confidence_label = confidence_label
        self.confidence_score = confidence_score
        self.data_quality_score = data_quality_score
        self.calls: list[tuple[int, datetime | None]] = []

    def predict_fixture_v3(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        model_dir: Path | str | None = None,
        v2_model_dir: Path | str | None = None,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: Any | None = None,
    ) -> PredictionV3Output:
        del model_dir, v2_model_dir, refresh_data, save_raw, api_client
        self.calls.append((fixture_id, prediction_time))
        if fixture_id in self.fail_fixture_ids:
            raise RuntimeError("synthetic daily v3 failure")
        fixture = self.session.get(models.Fixture, fixture_id)
        assert fixture is not None
        cutoff = prediction_time or NOW
        feature = models.V3FeatureSnapshot(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            feature_version="v3.0",
            official_lineup_available_flag=False,
            features_json={"synthetic": True},
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
        )
        self.session.add(feature)
        self.session.flush()
        prediction = models.V3ModelPrediction(
            fixture_id=fixture_id,
            v3_feature_snapshot_id=feature.id,
            prediction_time=cutoff,
            model_version="synthetic-v3-final",
            fusion_strategy="deterministic_fallback",
            p_v3_final_home=0.51,
            p_v3_final_draw=0.26,
            p_v3_final_away=0.23,
            p_v3_draw_risk=0.26,
            p_v3_home_no_draw=0.69,
            p_v3_away_no_draw=0.31,
            p_v2_home=1 / 3,
            p_v2_draw=1 / 3,
            p_v2_away=1 / 3,
            data_quality_score=self.data_quality_score,
            official_lineup_available_flag=False,
            confidence_score=self.confidence_score,
            confidence_label=self.confidence_label,
            predicted_result="HOME",
            expert_probabilities_json={},
            explanations_json={},
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            payload_json={"model_family": "v3"},
        )
        self.session.add(prediction)
        self.session.flush()
        return PredictionV3Output(
            fixture_id=fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition="Synthetic Daily V3 League",
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=ProbabilityTriple(0.51, 0.26, 0.23),
            predicted_result="HOME",
            confidence_label=self.confidence_label,
            confidence_score=self.confidence_score,
            model_version="synthetic-v3-final",
            fusion_strategy="deterministic_fallback",
            draw_risk_probability=0.26,
            home_no_draw_probability=0.69,
            away_no_draw_probability=0.31,
            v2_probabilities=ProbabilityTriple.uniform(),
            draw_risk_label="moyen",
            no_draw_winner_label="Home",
            top_factors_draw_risk=[{"name": "draw_risk_synthetic", "value": 0.5}],
            top_factors_no_draw_winner=[{"name": "ndw_synthetic", "value": 0.7}],
            explanations=["Prediction V3 synthétique quotidienne"],
            data_quality=DataQuality(),
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            key_absences_json={"home": [], "away": []},
            v3_feature_snapshot_id=feature.id,
            v3_model_prediction_id=prediction.id,
        )


def test_run_daily_v3_shadow_logs_v3_without_discord_or_v2_prediction(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_shadow.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(None)  # type: ignore[arg-type]

    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window=DailyPredictionWindow.NOW,
            send_discord=False,
            refresh_data=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        v2_count = session.scalar(select(func.count()).select_from(models.ModelPrediction))
        v3_predictions = list(session.execute(select(models.V3ModelPrediction)).scalars())

    assert summary.mode == "v3"
    assert summary.shadow_mode is True
    assert summary.total == 2
    assert summary.success == 2
    assert {result.status for result in summary.results} == {"shadow_logged"}
    assert all(result.v3_model_prediction_id is not None for result in summary.results)
    assert v2_count == 0
    assert len(v3_predictions) == 2
    assert all(row.payload_json["shadow_mode"] is True for row in v3_predictions)
    assert all(row.payload_json["daily_window"] == "now" for row in v3_predictions)


def test_run_daily_v3_dry_run_persists_discord_metadata_without_http_send(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_dry_run.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(None)  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        message = session.scalar(select(models.DiscordMessage))

    assert summary.success == 2
    assert summary.sent == 0
    assert calls == 0
    assert message is not None
    assert message.status == "dry_run"
    assert message.model_prediction_id is None
    assert message.payload_json["model_family"] == "v3"
    assert message.payload_json["v3_model_prediction_id"] is not None
    assert message.payload_json["shadow_mode"] is True
    assert message.payload_json["publication_decision"]["allowed"] is True


def test_run_daily_v3_production_sends_real_discord_and_v3_metadata(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_production.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(None)  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            shadow_mode=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        v2_count = session.scalar(select(func.count()).select_from(models.ModelPrediction))
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        v3_predictions = list(session.execute(select(models.V3ModelPrediction)).scalars())

    assert summary.mode == "v3"
    assert summary.shadow_mode is False
    assert summary.total == 2
    assert summary.sent == 2
    assert summary.success == 2
    assert calls == 2
    assert v2_count == 0
    assert len(messages) == 2
    assert len(v3_predictions) == 2
    assert all(message.status == "sent" for message in messages)
    assert all(message.model_prediction_id is None for message in messages)
    assert all(message.payload_json["model_family"] == "v3" for message in messages)
    assert all(message.payload_json["shadow_mode"] is False for message in messages)
    assert all(message.payload_json["daily_window"] == "now" for message in messages)
    assert all(message.payload_json["v3_model_prediction_id"] is not None for message in messages)
    assert all(row.payload_json["shadow_mode"] is False for row in v3_predictions)


def test_run_daily_v3_low_confidence_stays_internal_without_discord(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_low_confidence.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(
        None,
        confidence_label="Low",
        confidence_score=18.0,
    )  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            shadow_mode=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        v3_predictions = list(session.execute(select(models.V3ModelPrediction)).scalars())

    assert summary.total == 2
    assert summary.confidence_skipped == 2
    assert summary.sent == 0
    assert calls == 0
    assert messages == []
    assert len(v3_predictions) == 2
    assert {result.status for result in summary.results} == {"confidence_skipped"}
    assert {
        result.reason for result in summary.results
    } == {"confidence_below_publish_threshold"}


def test_run_daily_v3_high_confidence_low_quality_stays_internal_without_discord(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_low_quality.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(
        None,
        confidence_label="High",
        confidence_score=72.0,
        data_quality_score=59.0,
    )  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            shadow_mode=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        v3_predictions = list(session.execute(select(models.V3ModelPrediction)).scalars())

    assert summary.confidence_skipped == 2
    assert summary.sent == 0
    assert calls == 0
    assert messages == []
    assert {result.reason for result in summary.results} == {
        "data_quality_below_publish_threshold"
    }
    assert all(
        row.payload_json["non_publication_reason"] == "data_quality_below_publish_threshold"
        for row in v3_predictions
    )


def test_run_daily_v3_production_skips_existing_sent_window_duplicate(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_dedupe.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionV3Service(None)  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        session.add(
            models.DiscordMessage(
                fixture_id=-1,
                model_prediction_id=None,
                status="sent",
                league_id=-100,
                season=2026,
                channel_key="predictions",
                message_type="prediction",
                dry_run=False,
                print_only=False,
                message_hash="existing-v3-window",
                message_markdown="existing synthetic V3 message",
                route_json={},
                response_json={"status_code": 204},
                payload_json={
                    "model_family": "v3",
                    "daily_window": "now",
                    "v3_model_prediction_id": -12345,
                },
            )
        )
        session.flush()
        summary = run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            shadow_mode=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        sent_messages = list(
            session.execute(
                select(models.DiscordMessage).where(models.DiscordMessage.status == "sent")
            ).scalars()
        )

    statuses_by_fixture = {result.fixture_id: result.status for result in summary.results}
    reasons_by_fixture = {result.fixture_id: result.reason for result in summary.results}
    assert summary.total == 2
    assert summary.sent == 1
    assert summary.duplicate_skipped == 1
    assert statuses_by_fixture[-1] == "duplicate_skipped"
    assert reasons_by_fixture[-1] == "sent_prediction_window"
    assert statuses_by_fixture[-2] == "sent"
    assert calls == 1
    assert fake_service.calls == [(-2, NOW)]
    assert len(sent_messages) == 2


def test_run_daily_v3_shadow_blocks_live_discord_send(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_v3_blocks_live.db'}")
    session_factory = create_session_factory(engine)

    with (
        session_scope(session_factory) as session,
        pytest.raises(PredictionError, match="shadow mode"),
    ):
        run_daily_predictions_v3(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/v3-daily",
            ),
            prediction_service_factory=lambda _session: FakePredictionV3Service(_session),
            now=NOW,
        )


def test_predict_today_v3_cli_blocks_live_discord_without_production_mode() -> None:
    result = CliRunner().invoke(app, ["predict-today-v3", "--send-discord"])

    assert result.exit_code != 0
    assert "shadow mode blocks live Discord sends" in result.output


def test_predict_today_v3_cli_json_and_print_only_persists_discord_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "daily_v3_cli.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_teams(session)
        _seed_fixture(session, -3000, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), 39, 2025)

    def fake_v3_service(session, *_args, **_kwargs) -> FakePredictionV3Service:
        return FakePredictionV3Service(session)

    monkeypatch.setattr(
        "football_predictor.prediction.run_daily._prediction_v3_service",
        fake_v3_service,
    )
    output_path = tmp_path / "summary.json"
    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict-today-v3",
            "--date",
            "2026-05-02",
            "--prediction-time",
            NOW.isoformat(),
            "--window",
            "late",
            "--league",
            "39",
            "--season",
            "2025",
            "--no-refresh-data",
            "--dry-run",
            "--print-only",
            "--json-output",
            str(output_path),
            "--json",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "v3"
    assert payload["shadow_mode"] is True
    assert payload["predicted"] == 1
    assert payload["results"][0]["v3_model_prediction_id"] is not None
    with session_scope(session_factory) as session:
        message = session.scalar(select(models.DiscordMessage))
    assert message is not None
    assert message.status == "print_only"
    assert message.model_prediction_id is None
    assert message.payload_json["v3_model_prediction_id"] == payload["results"][0][
        "v3_model_prediction_id"
    ]


def _seed_fixtures(session, *, league_id: int, season: int) -> None:
    _seed_teams(session)
    _seed_fixture(session, -1, datetime(2026, 5, 2, 12, 0, tzinfo=UTC), league_id, season)
    _seed_fixture(session, -2, datetime(2026, 5, 2, 20, 0, tzinfo=UTC), league_id, season)
    _seed_fixture(
        session,
        -3,
        datetime(2026, 5, 2, 22, 0, tzinfo=UTC),
        league_id,
        season,
        status="FT",
    )


def _seed_fixture(
    session,
    fixture_id: int,
    kickoff: datetime,
    league_id: int,
    season: int,
    status: str = "NS",
) -> None:
    session.add(
        models.Fixture(
            fixture_id=fixture_id,
            date=kickoff,
            league_id=league_id,
            season=season,
            status=status,
            status_short=status,
            home_team_id=-10,
            away_team_id=-20,
            home_team=f"Synthetic Home {fixture_id}",
            away_team=f"Synthetic Away {fixture_id}",
            payload_json={"synthetic": True},
        )
    )


def _seed_teams(session) -> None:
    session.add_all(
        [
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}),
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}),
        ]
    )
