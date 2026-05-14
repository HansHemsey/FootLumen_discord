from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.run_daily import (
    get_fixtures_to_predict,
    run_daily_predictions,
)
from football_predictor.prediction.scheduler import (
    DailyPredictionWindow,
    fixture_matches_window,
    prediction_time_for_fixture,
)
from football_predictor.prediction.service import PredictionOutput
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.exceptions import ReferenceLookupError

NOW = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
TARGET_DATE = date(2026, 5, 2)


class FakePredictionService:
    def __init__(
        self,
        session,
        *,
        fail_fixture_ids: set[int] | None = None,
        confidence_label: str = "High",
        confidence_score: float = 72.0,
        data_quality_score: float = 75.0,
    ) -> None:
        self.session = session
        self.fail_fixture_ids = fail_fixture_ids or set()
        self.confidence_label = confidence_label
        self.confidence_score = confidence_score
        self.data_quality_score = data_quality_score
        self.calls: list[tuple[int, datetime | None]] = []

    def predict_fixture(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        model_dir: Path | str | None = None,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: Any | None = None,
    ) -> PredictionOutput:
        del model_dir, refresh_data, save_raw, api_client
        self.calls.append((fixture_id, prediction_time))
        if fixture_id in self.fail_fixture_ids:
            raise RuntimeError("synthetic run_daily failure")
        fixture = self.session.get(models.Fixture, fixture_id)
        assert fixture is not None
        cutoff = prediction_time or NOW
        feature = models.FeatureSnapshot(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            feature_version=f"run_daily_fake_{fixture_id}_{len(self.calls)}",
            features_json={"synthetic": True},
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
        )
        self.session.add(feature)
        self.session.flush()
        prediction = models.ModelPrediction(
            fixture_id=fixture_id,
            feature_snapshot_id=feature.id,
            prediction_time=cutoff,
            model_version="synthetic-daily-model",
            p_home=0.48,
            p_draw=0.27,
            p_away=0.25,
            predicted_outcome="HOME",
            predicted_result="HOME",
            confidence=42.0,
            confidence_label=self.confidence_label,
            confidence_score=self.confidence_score,
            explanation_json=["Prediction synthétique quotidienne"],
            explanations_json=["Prediction synthétique quotidienne"],
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            payload_json={"synthetic": True},
        )
        self.session.add(prediction)
        self.session.flush()
        return PredictionOutput(
            fixture_id=fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition="Synthetic Daily League",
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=ProbabilityTriple(0.48, 0.27, 0.25),
            predicted_result="HOME",
            confidence_label=self.confidence_label,
            confidence_score=self.confidence_score,
            explanations=["Prediction synthétique quotidienne"],
            data_quality=DataQuality(),
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            model_version="synthetic-daily-model",
            feature_snapshot_id=feature.id,
            model_prediction_id=prediction.id,
        )


class FakeApiClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        self.calls.append((endpoint, params))
        return ApiFootballPayload(
            endpoint=endpoint,
            params=dict(params or {}),
            payload={"response": []},
            fetched_at=NOW.isoformat(),
            status_code=200,
        )


class ExplodingApiClient:
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> ApiFootballPayload:
        del save_raw
        raise AssertionError(f"Unexpected API call endpoint={endpoint} params={params}")


def test_prediction_time_windows() -> None:
    kickoff = datetime(2026, 5, 2, 20, 0, tzinfo=UTC)

    assert prediction_time_for_fixture(kickoff, "early") == datetime(
        2026, 5, 1, 20, 0, tzinfo=UTC
    )
    assert prediction_time_for_fixture(kickoff, "mid") == datetime(
        2026, 5, 2, 14, 0, tzinfo=UTC
    )
    assert prediction_time_for_fixture(kickoff, "late", now=NOW) == NOW
    assert prediction_time_for_fixture(kickoff, "now", now=NOW) == NOW


def test_fixture_matches_daily_windows() -> None:
    past = datetime(2026, 5, 2, 9, 59, tzinfo=UTC)
    late = datetime(2026, 5, 2, 10, 30, tzinfo=UTC)
    outside_late = datetime(2026, 5, 2, 10, 31, tzinfo=UTC)
    mid = datetime(2026, 5, 2, 13, 0, tzinfo=UTC)
    early = datetime(2026, 5, 2, 18, 30, tzinfo=UTC)

    assert not fixture_matches_window(past, "now", NOW)
    assert fixture_matches_window(late, "late", NOW)
    assert not fixture_matches_window(outside_late, "late", NOW)
    assert not fixture_matches_window(mid, "late", NOW)
    assert fixture_matches_window(mid, "mid", NOW)
    assert not fixture_matches_window(early, "mid", NOW)
    assert fixture_matches_window(early, "early", NOW)
    assert fixture_matches_window(late, "now", NOW)
    assert fixture_matches_window(early, "all", NOW)


def test_get_fixtures_to_predict_filters_status_and_competitions(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_filter.db'}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_fixtures(session, league_id=-100, season=2026)
        fixtures = get_fixtures_to_predict(
            TARGET_DATE,
            session=session,
            competitions=(_competition(-100, enabled=True), _competition(-200, enabled=False)),
        )

    assert [fixture.fixture_id for fixture in fixtures] == [-1, -2]


def test_get_fixtures_to_predict_validates_real_league_id(
    reference_path: Path,
    tmp_path: Path,
) -> None:
    reference = load_api_football_reference(reference_path)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_reference.db'}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        assert (
            get_fixtures_to_predict(
                TARGET_DATE,
                league_ids=(39,),
                session=session,
                reference=reference,
            )
            == []
        )
        with pytest.raises(ReferenceLookupError):
            get_fixtures_to_predict(
                TARGET_DATE,
                league_ids=(999999,),
                season=2099,
                session=session,
                reference=reference,
            )


def test_run_daily_no_refresh_does_not_call_api_and_dry_run_does_not_send(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_dry_run.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window=DailyPredictionWindow.NOW,
            send_discord=True,
            refresh_data=False,
            dry_run=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            api_client=ExplodingApiClient(),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert summary.total == 2
    assert summary.success == 2
    assert summary.sent == 0
    assert calls == 0


def test_run_daily_filters_fixtures_by_window(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_windows.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        session.merge(
            models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True})
        )
        session.merge(
            models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True})
        )
        _fixture(session, -11, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), -100, 2026, "NS")
        _fixture(session, -12, datetime(2026, 5, 2, 13, 0, tzinfo=UTC), -100, 2026, "NS")
        _fixture(session, -13, datetime(2026, 5, 2, 18, 30, tzinfo=UTC), -100, 2026, "NS")
        _fixture(session, -14, datetime(2026, 5, 2, 9, 0, tzinfo=UTC), -100, 2026, "NS")
        fake_service = FakePredictionService(session)

        summaries = {
            window: run_daily_predictions(
                TARGET_DATE,
                league_ids=(-100,),
                window=window,
                send_discord=False,
                refresh_data=False,
                session=session,
                reference=ApiFootballReference({"competitions": [], "references": {}}),
                prediction_service_factory=lambda _run_session: fake_service,
                now=NOW,
            )
            for window in ("late", "mid", "early", "now", "all")
        }

    assert [result.fixture_id for result in summaries["late"].results] == [-11]
    assert [result.fixture_id for result in summaries["mid"].results] == [-12]
    assert [result.fixture_id for result in summaries["early"].results] == [-13]
    assert [result.fixture_id for result in summaries["now"].results] == [-11, -12, -13]
    assert [result.fixture_id for result in summaries["all"].results] == [-11, -12, -13]


def test_run_daily_continues_after_fixture_error(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_failure.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None, fail_fixture_ids={-2})  # type: ignore[arg-type]
    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=False,
            refresh_data=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert summary.total == 2
    assert summary.success == 1
    assert summary.failed == 1
    assert {result.status for result in summary.results} == {"predicted", "failed"}


def test_run_daily_deduplicates_only_after_real_discord_send(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_dedupe.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        feature = models.FeatureSnapshot(
            fixture_id=-1,
            prediction_time=NOW,
            feature_version="existing_daily_feature",
            features_json={},
            data_quality_json={},
        )
        session.add(feature)
        session.flush()
        prediction = models.ModelPrediction(
            fixture_id=-1,
            feature_snapshot_id=feature.id,
            prediction_time=NOW,
            model_version="synthetic-daily-model",
            p_home=0.48,
            p_draw=0.27,
            p_away=0.25,
            predicted_outcome="HOME",
            predicted_result="HOME",
            confidence=42.0,
            confidence_label="Medium",
            confidence_score=42.0,
            explanation_json=[],
            explanations_json=[],
            data_quality_json={},
            payload_json={"daily_window": "now"},
        )
        session.add(prediction)
        session.flush()
        session.add(
            models.DiscordMessage(
                fixture_id=-1,
                model_prediction_id=prediction.id,
                league_id=-100,
                season=2026,
                channel_key="predictions",
                message_type="prediction",
                status="sent",
                dry_run=False,
                print_only=False,
                webhook_hash="synthetic",
                webhook_url_hash="synthetic",
                message_hash="synthetic-sent",
                message_markdown="```md\nsent\n```",
                payload_json={"daily_window": "now"},
                route_json={},
                response_json={},
            )
        )
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    statuses = {result.fixture_id: result.status for result in summary.results}
    assert statuses[-1] == "duplicate_skipped"
    assert statuses[-2] == "sent"
    assert calls == 1
    assert summary.skipped == 1
    assert summary.sent == 1


def test_run_daily_dry_run_prediction_does_not_block_future_real_send(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_dry_run_then_real.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _fixture(session, -11, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), -100, 2026, "NS")
        run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="late",
            send_discord=True,
            refresh_data=False,
            dry_run=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        real = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="late",
            send_discord=True,
            refresh_data=False,
            dry_run=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert real.sent == 1
    assert calls == 1


def test_run_daily_live_skips_high_confidence_with_low_data_quality(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_low_quality.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(
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
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        messages = list(session.execute(select(models.DiscordMessage)).scalars())
        predictions = list(session.execute(select(models.ModelPrediction)).scalars())

    assert summary.confidence_skipped == 2
    assert summary.sent == 0
    assert calls == 0
    assert messages == []
    assert {result.reason for result in summary.results} == {
        "data_quality_below_publish_threshold"
    }
    assert all(
        prediction.payload_json["non_publication_reason"]
        == "data_quality_below_publish_threshold"
        for prediction in predictions
    )


def test_run_daily_live_skips_medium_confidence_even_with_high_quality(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_medium_quality.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(
        None,
        confidence_label="Medium",
        confidence_score=55.0,
        data_quality_score=90.0,
    )  # type: ignore[arg-type]
    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http_client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="now",
            send_discord=True,
            refresh_data=False,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
                http_client=http_client,
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert summary.confidence_skipped == 2
    assert calls == 0
    assert {result.reason for result in summary.results} == {
        "confidence_below_publish_threshold"
    }


def test_run_daily_dry_run_persists_publication_decision_for_non_publishable_prediction(
    tmp_path: Path,
) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_dry_run_policy.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(
        None,
        confidence_label="Medium",
        confidence_score=55.0,
        data_quality_score=50.0,
    )  # type: ignore[arg-type]
    with session_scope(session_factory) as session:
        fake_service.session = session
        _fixture(session, -11, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), -100, 2026, "NS")
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            window="late",
            send_discord=True,
            refresh_data=False,
            dry_run=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/daily",
            ),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )
        message = session.scalar(select(models.DiscordMessage))

    assert summary.success == 1
    assert message is not None
    assert message.status == "dry_run"
    assert message.payload_json["publication_decision"]["allowed"] is False
    assert message.payload_json["non_publication_reason"] == (
        "confidence_below_publish_threshold"
    )


def test_run_daily_refresh_uses_mock_api_client(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_refresh.db'}")
    session_factory = create_session_factory(engine)
    client = FakeApiClient()
    with session_scope(session_factory) as session:
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            season=2026,
            window="now",
            send_discord=False,
            refresh_data=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            api_client=client,
            prediction_service_factory=lambda _session: FakePredictionService(_session),
            now=NOW,
        )

    assert summary.total == 0
    assert client.calls == [("/fixtures", {"date": "2026-05-02", "league": -100, "season": 2026})]


def test_run_daily_late_recomputes_prediction_time_after_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import football_predictor.prediction.run_daily as run_daily_module

    after_refresh = datetime(2026, 5, 2, 10, 0, 5, tzinfo=UTC)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_late_cutoff.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    monkeypatch.setattr(
        run_daily_module,
        "_refresh_fixtures_for_date",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(run_daily_module, "_refresh_fixture_inputs", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_daily_module, "utc_now", lambda: after_refresh)

    with session_scope(session_factory) as session:
        fake_service.session = session
        _fixture(session, -11, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), -100, 2026, "NS")
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            season=2026,
            window="late",
            send_discord=False,
            refresh_data=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            api_client=FakeApiClient(),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert summary.success == 1
    assert fake_service.calls == [(-11, after_refresh)]


def test_run_daily_mid_keeps_simulated_prediction_time_after_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import football_predictor.prediction.run_daily as run_daily_module

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'daily_mid_cutoff.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    monkeypatch.setattr(
        run_daily_module,
        "_refresh_fixtures_for_date",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(run_daily_module, "_refresh_fixture_inputs", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        run_daily_module,
        "utc_now",
        lambda: datetime(2026, 5, 2, 10, 0, 5, tzinfo=UTC),
    )

    kickoff = datetime(2026, 5, 2, 13, 0, tzinfo=UTC)
    with session_scope(session_factory) as session:
        fake_service.session = session
        _fixture(session, -12, kickoff, -100, 2026, "NS")
        summary = run_daily_predictions(
            TARGET_DATE,
            league_ids=(-100,),
            season=2026,
            window="mid",
            send_discord=False,
            refresh_data=True,
            session=session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            api_client=FakeApiClient(),
            prediction_service_factory=lambda _session: fake_service,
            now=NOW,
        )

    assert summary.success == 1
    assert fake_service.calls == [(-12, datetime(2026, 5, 2, 7, 0, tzinfo=UTC))]


def _competition(
    league_id: int,
    *,
    season: int = 2026,
    enabled: bool = True,
) -> CompetitionConfig:
    return CompetitionConfig(
        key="synthetic",
        league_id=league_id,
        season=season,
        name="Synthetic League",
        country="Synthetic",
        enabled=enabled,
        source="synthetic",
    )


def _seed_fixtures(session, *, league_id: int, season: int) -> None:
    session.merge(models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}))
    session.merge(models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}))
    _fixture(session, -1, datetime(2026, 5, 2, 12, 0, tzinfo=UTC), league_id, season, "NS")
    _fixture(session, -2, datetime(2026, 5, 2, 20, 0, tzinfo=UTC), league_id, season, "TBD")
    _fixture(session, -3, datetime(2026, 5, 2, 22, 0, tzinfo=UTC), league_id, season, "FT")
    _fixture(session, -4, datetime(2026, 5, 3, 12, 0, tzinfo=UTC), league_id, season, "NS")


def _fixture(
    session,
    fixture_id: int,
    kickoff: datetime,
    league_id: int,
    season: int,
    status: str,
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
