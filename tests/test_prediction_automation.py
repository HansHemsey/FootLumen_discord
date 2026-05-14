from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from football_predictor.api.api_football_client import ApiFootballPayload
from football_predictor.cli import app
from football_predictor.config.competitions import CompetitionConfig
from football_predictor.config.settings import get_settings
from football_predictor.db import models
from football_predictor.db.init_db import create_db_and_tables
from football_predictor.db.session import create_session_factory, session_scope
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.features.data_quality import DataQuality
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.automation import (
    AutomationRunConfig,
    PredictionAutomationService,
    PredictionWindow,
)
from football_predictor.prediction.service import PredictionOutput
from football_predictor.reference.loaders import load_api_football_reference
from football_predictor.reference.lookups import ApiFootballReference
from football_predictor.utils.exceptions import ReferenceLookupError

PREDICTION_TIME = datetime(2026, 5, 2, 10, tzinfo=UTC)
TARGET_DATE = PREDICTION_TIME.date()


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
        self.calls = 0

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
        self.calls += 1
        if fixture_id in self.fail_fixture_ids:
            raise RuntimeError("synthetic prediction failure")
        fixture = self.session.get(models.Fixture, fixture_id)
        assert fixture is not None
        cutoff = prediction_time or PREDICTION_TIME
        feature = models.FeatureSnapshot(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            feature_version=f"automation_fake_{fixture_id}_{self.calls}",
            features_json={"synthetic": True},
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
        )
        self.session.add(feature)
        self.session.flush()
        prediction = models.ModelPrediction(
            fixture_id=fixture_id,
            prediction_time=cutoff,
            model_version="synthetic-automation",
            feature_snapshot_id=feature.id,
            p_home=0.50,
            p_draw=0.25,
            p_away=0.25,
            predicted_outcome="HOME",
            predicted_result="HOME",
            confidence=45.0,
            confidence_label=self.confidence_label,
            confidence_score=self.confidence_score,
            explanation_json=["Synthetic automation prediction"],
            explanations_json=["Synthetic automation prediction"],
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            payload_json={"synthetic": True},
        )
        self.session.add(prediction)
        self.session.flush()
        return PredictionOutput(
            fixture_id=fixture_id,
            match_label=f"{fixture.home_team} vs {fixture.away_team}",
            competition="Synthetic Competition",
            match_date=fixture.date,
            prediction_time=cutoff,
            probabilities=ProbabilityTriple(0.50, 0.25, 0.25),
            predicted_result="HOME",
            confidence_label=self.confidence_label,
            confidence_score=self.confidence_score,
            explanations=["Synthetic automation prediction"],
            data_quality=DataQuality(),
            data_quality_json={"overall_data_quality_score": self.data_quality_score},
            model_version="synthetic-automation",
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
            fetched_at=PREDICTION_TIME.isoformat(),
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


def test_automation_filters_prediction_windows_and_skips_started(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            prediction_service_factory=lambda _session: fake_service,
        ).run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
            )
        )

    assert summary.found == 5
    assert summary.predicted == 1
    assert summary.skipped == 4
    predicted = [item for item in summary.results if item.status == "predicted"]
    assert [item.fixture_id for item in predicted] == [-3]
    assert {item.reason for item in summary.results if item.status == "skipped"} >= {
        "outside_late_window",
        "already_started",
        "status_ft",
    }


def test_automation_all_window_predicts_all_future_fixtures(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_all.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            prediction_service_factory=lambda _session: fake_service,
        ).run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.ALL,
            )
        )

    assert summary.predicted == 3
    assert [item.fixture_id for item in summary.results if item.status == "predicted"] == [
        -3,
        -2,
        -1,
    ]


def test_automation_continues_when_one_fixture_fails(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_fail.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None, fail_fixture_ids={-2})  # type: ignore[arg-type]

    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            prediction_service_factory=lambda _session: fake_service,
        ).run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.ALL,
            )
        )

    assert summary.predicted == 2
    assert summary.failed == 1
    failed = [item for item in summary.results if item.status == "failed"]
    assert failed[0].fixture_id == -2


def test_automation_no_refresh_never_calls_api(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_no_refresh.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    with session_scope(session_factory) as session:
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        summary = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            api_client=ExplodingApiClient(),
            prediction_service_factory=lambda _session: fake_service,
        ).run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                refresh_data=False,
            )
        )

    assert summary.predicted == 1


def test_automation_refresh_uses_mock_client_params(tmp_path: Path) -> None:
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_refresh.db'}")
    session_factory = create_session_factory(engine)
    client = FakeApiClient()

    with session_scope(session_factory) as session:
        summary = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            api_client=client,
            prediction_service_factory=lambda _session: FakePredictionService(_session),
        ).run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.ALL,
                refresh_data=True,
            )
        )

    assert summary.found == 0
    assert client.calls == [("/fixtures", {"date": "2026-05-02", "league": -100, "season": 2026})]


def test_automation_validates_real_league_ids(reference_path: Path, tmp_path: Path) -> None:
    reference = load_api_football_reference(reference_path)
    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_reference.db'}")
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        service = PredictionAutomationService(session, reference=reference)
        summary = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                leagues=(39,),
                season=2025,
            )
        )
        assert summary.leagues == (39,)
        with pytest.raises(ReferenceLookupError):
            service.run(
                AutomationRunConfig(
                    target_date=TARGET_DATE,
                    prediction_time=PREDICTION_TIME,
                    leagues=(-999,),
                    season=2099,
                )
            )


def test_automation_discord_dedupe_and_dry_run_semantics(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_discord.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(None)  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        delivery = DiscordDeliveryService(
            session,
            legacy_webhook_url="https://example.invalid/automation-webhook",
            http_client=client,
        )
        service = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            discord_delivery=delivery,
            prediction_service_factory=lambda _session: fake_service,
        )
        dry_run = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
                dry_run=True,
            )
        )
        print_only = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
                print_only=True,
            )
        )
        first_send = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
            )
        )
        duplicate = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
            )
        )
        forced = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
                force=True,
            )
        )

    assert _status_for_fixture(dry_run, -3) == "dry_run"
    assert _status_for_fixture(print_only, -3) == "print_only"
    assert _status_for_fixture(first_send, -3) == "sent"
    assert _status_for_fixture(duplicate, -3) == "duplicate_skipped"
    assert _status_for_fixture(forced, -3) == "sent"
    assert calls == 2


def test_automation_live_skips_non_publishable_prediction_without_discord_send(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(204)

    engine = create_db_and_tables(f"sqlite:///{tmp_path / 'automation_policy.db'}")
    session_factory = create_session_factory(engine)
    fake_service = FakePredictionService(
        None,
        confidence_label="High",
        confidence_score=72.0,
        data_quality_score=59.0,
    )  # type: ignore[arg-type]

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        session_scope(session_factory) as session,
    ):
        fake_service.session = session
        _seed_fixtures(session, league_id=-100, season=2026)
        service = PredictionAutomationService(
            session,
            reference=ApiFootballReference({"competitions": [], "references": {}}),
            competitions=(_competition(-100),),
            discord_delivery=DiscordDeliveryService(
                session,
                legacy_webhook_url="https://example.invalid/automation-webhook",
                http_client=client,
            ),
            prediction_service_factory=lambda _session: fake_service,
        )
        summary = service.run(
            AutomationRunConfig(
                target_date=TARGET_DATE,
                prediction_time=PREDICTION_TIME,
                window=PredictionWindow.LATE,
                send_discord=True,
            )
        )
        prediction = session.scalar(select(models.ModelPrediction))

    assert _status_for_fixture(summary, -3) == "confidence_skipped"
    assert summary.confidence_skipped == 1
    assert calls == 0
    assert prediction is not None
    assert prediction.payload_json["non_publication_reason"] == (
        "data_quality_below_publish_threshold"
    )


def test_predict_today_cli_writes_json_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "automation_cli.db"
    engine = create_db_and_tables(f"sqlite:///{db_path}")
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        _seed_teams(session)
        _fixture(session, -3000, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), 39, 2025, "NS")

    class CliFakePredictionService:
        def __init__(self, _reference, session, **_kwargs) -> None:
            self._fake = FakePredictionService(session)

        def predict_fixture(self, *args, **kwargs) -> PredictionOutput:
            return self._fake.predict_fixture(*args, **kwargs)

    monkeypatch.setattr(
        "football_predictor.prediction.run_daily.PredictionService",
        CliFakePredictionService,
    )
    output_path = tmp_path / "summary.json"
    get_settings.cache_clear()
    result = CliRunner().invoke(
        app,
        [
            "predict-today",
            "--date",
            "2026-05-02",
            "--prediction-time",
            PREDICTION_TIME.isoformat(),
            "--window",
            "late",
            "--league",
            "39",
            "--season",
            "2025",
            "--no-refresh-data",
            "--dry-run",
            "--json-output",
            str(output_path),
            "--json",
        ],
        env={"DATABASE_URL": f"sqlite:///{db_path}"},
    )
    get_settings.cache_clear()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["leagues"] == [39]
    assert payload["predicted"] == 1
    assert payload["results"][0]["fixture_id"] == -3000


def _competition(league_id: int, season: int = 2026) -> CompetitionConfig:
    return CompetitionConfig(
        key="synthetic",
        league_id=league_id,
        season=season,
        name="Synthetic Competition",
        country="Synthetic",
        enabled=True,
        source="synthetic",
    )


def _status_for_fixture(summary, fixture_id: int) -> str:
    for item in summary.results:
        if item.fixture_id == fixture_id:
            return item.status
    raise AssertionError(f"fixture_id={fixture_id} missing from summary")


def _seed_fixtures(session, *, league_id: int, season: int) -> None:
    _seed_teams(session)
    _fixture(session, -1, datetime(2026, 5, 2, 20, tzinfo=UTC), league_id, season, "NS")
    _fixture(session, -2, datetime(2026, 5, 2, 13, tzinfo=UTC), league_id, season, "NS")
    _fixture(session, -3, datetime(2026, 5, 2, 10, 30, tzinfo=UTC), league_id, season, "NS")
    _fixture(session, -4, datetime(2026, 5, 2, 9, 30, tzinfo=UTC), league_id, season, "NS")
    _fixture(session, -5, datetime(2026, 5, 2, 11, tzinfo=UTC), league_id, season, "FT")
    _fixture(session, -6, datetime(2026, 5, 3, 10, 30, tzinfo=UTC), league_id, season, "NS")


def _seed_teams(session) -> None:
    session.merge(models.Team(team_id=-10, name="Synthetic Home", payload_json={"synthetic": True}))
    session.merge(models.Team(team_id=-20, name="Synthetic Away", payload_json={"synthetic": True}))


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
