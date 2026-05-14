"""Daily prediction automation orchestration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.discord.service import DiscordDeliveryService, DiscordSendResult
from football_predictor.ingestion.fixtures import FixtureIngestionService
from football_predictor.prediction.publication_flow import publication_metadata
from football_predictor.prediction.publication_policy import (
    DEFAULT_MIN_DATA_QUALITY_SCORE,
    PublicationDecision,
    evaluate_publication,
)
from football_predictor.prediction.service import (
    ApiFootballPayloadClient,
    PredictionOutput,
    PredictionService,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]

UPCOMING_STATUSES = {"", "NS", "TBD"}


class PredictionWindow(StrEnum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    NOW = "now"
    ALL = "all"


@dataclass(frozen=True)
class AutomationRunConfig:
    target_date: date | None = None
    prediction_time: datetime | None = None
    window: PredictionWindow | str = PredictionWindow.ALL
    leagues: tuple[int, ...] = ()
    season: int | None = None
    model_dir: Path | None = None
    refresh_data: bool = False
    send_discord: bool = False
    dry_run: bool = False
    print_only: bool = False
    force: bool = False
    limit: int | None = None
    save_raw: bool = False
    min_data_quality_score: float = DEFAULT_MIN_DATA_QUALITY_SCORE


@dataclass(frozen=True)
class AutomationFixtureResult:
    fixture_id: int
    status: str
    kickoff: datetime | None = None
    league_id: int | None = None
    season: int | None = None
    reason: str | None = None
    predicted_result: str | None = None
    model_prediction_id: int | None = None
    discord_message_id: int | None = None
    probabilities: dict[str, float] | None = None
    error: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "status": self.status,
            "kickoff": self.kickoff.isoformat() if self.kickoff else None,
            "league_id": self.league_id,
            "season": self.season,
            "reason": self.reason,
            "predicted_result": self.predicted_result,
            "model_prediction_id": self.model_prediction_id,
            "discord_message_id": self.discord_message_id,
            "probabilities": self.probabilities,
            "error": self.error,
        }


@dataclass(frozen=True)
class AutomationRunSummary:
    run_key: str
    target_date: date
    prediction_time: datetime
    window: PredictionWindow
    leagues: tuple[int, ...]
    season: int | None
    refresh_data: bool
    send_discord: bool
    results: list[AutomationFixtureResult] = field(default_factory=list)
    refresh_summary: JsonDict = field(default_factory=dict)

    @property
    def found(self) -> int:
        return len(self.results)

    @property
    def predicted(self) -> int:
        return sum(
            1
            for item in self.results
            if item.status in {"predicted", "sent", "dry_run", "print_only", "duplicate_skipped"}
            or item.status == "confidence_skipped"
        )

    @property
    def sent(self) -> int:
        return sum(1 for item in self.results if item.status == "sent")

    @property
    def skipped(self) -> int:
        return sum(1 for item in self.results if item.status == "skipped")

    @property
    def duplicate_skipped(self) -> int:
        return sum(1 for item in self.results if item.status == "duplicate_skipped")

    @property
    def confidence_skipped(self) -> int:
        return sum(1 for item in self.results if item.status == "confidence_skipped")

    @property
    def failed(self) -> int:
        return sum(1 for item in self.results if item.status == "failed")

    def as_dict(self) -> JsonDict:
        return {
            "run_key": self.run_key,
            "target_date": self.target_date.isoformat(),
            "prediction_time": self.prediction_time.isoformat(),
            "window": self.window.value,
            "leagues": list(self.leagues),
            "season": self.season,
            "refresh_data": self.refresh_data,
            "send_discord": self.send_discord,
            "found": self.found,
            "predicted": self.predicted,
            "sent": self.sent,
            "skipped": self.skipped,
            "duplicate_skipped": self.duplicate_skipped,
            "confidence_skipped": self.confidence_skipped,
            "failed": self.failed,
            "refresh_summary": self.refresh_summary,
            "results": [item.as_dict() for item in self.results],
        }


class PredictionServiceLike(Protocol):
    def predict_fixture(
        self,
        fixture_id: int,
        prediction_time: datetime | None = None,
        *,
        model_dir: Path | str | None = None,
        refresh_data: bool = False,
        save_raw: bool = False,
        api_client: ApiFootballPayloadClient | None = None,
    ) -> PredictionOutput:
        ...


PredictionServiceFactory = Callable[[Session], PredictionServiceLike]


class PredictionAutomationService:
    """Run daily prediction jobs without an internal scheduler."""

    def __init__(
        self,
        session: Session,
        *,
        reference: ApiFootballReference,
        players_reference: PlayersReference | None = None,
        competitions: Sequence[CompetitionConfig] = (),
        timezone_name: str = "Europe/Paris",
        api_client: ApiFootballPayloadClient | None = None,
        discord_delivery: DiscordDeliveryService | None = None,
        prediction_service_factory: PredictionServiceFactory | None = None,
    ) -> None:
        self.session = session
        self.reference = reference
        self.players_reference = players_reference
        self.competitions = tuple(competitions)
        self.timezone_name = timezone_name
        self.api_client = api_client
        self.discord_delivery = discord_delivery
        self.prediction_service_factory = prediction_service_factory

    def run(self, config: AutomationRunConfig) -> AutomationRunSummary:
        prediction_time = ensure_aware_utc(config.prediction_time or utc_now())
        local_timezone = ZoneInfo(self.timezone_name)
        target_date = config.target_date or prediction_time.astimezone(local_timezone).date()
        window = PredictionWindow(str(config.window))
        competitions = self._resolve_competitions(config)
        run_key = _run_key(target_date, window, competitions)
        refresh_summary: JsonDict = {}

        if config.refresh_data:
            if self.api_client is None:
                raise PredictionError("refresh_data=True requires an API-Football client")
            refresh_summary = self._refresh_fixtures(target_date, competitions, config.save_raw)

        candidates = self._candidate_fixtures(target_date, competitions, local_timezone)
        selected: list[models.Fixture] = []
        results: list[AutomationFixtureResult] = []
        for fixture in candidates:
            reason = _skip_reason(fixture, prediction_time, target_date, window, local_timezone)
            if reason is not None:
                results.append(_skipped_result(fixture, reason))
            else:
                selected.append(fixture)

        if config.limit is not None:
            limited = selected[: config.limit]
            for fixture in selected[config.limit :]:
                results.append(_skipped_result(fixture, "limit"))
            selected = limited

        prediction_service = self._prediction_service()
        for fixture in selected:
            results.append(
                self._predict_one(
                    fixture,
                    prediction_service,
                    config=config,
                    prediction_time=prediction_time,
                    run_key=run_key,
                    target_date=target_date,
                    window=window,
                )
            )

        return AutomationRunSummary(
            run_key=run_key,
            target_date=target_date,
            prediction_time=prediction_time,
            window=window,
            leagues=tuple(competition.league_id for competition in competitions),
            season=config.season,
            refresh_data=config.refresh_data,
            send_discord=config.send_discord,
            results=sorted(
                results,
                key=lambda item: (
                    item.kickoff or datetime.max.replace(tzinfo=UTC),
                    item.fixture_id,
                ),
            ),
            refresh_summary=refresh_summary,
        )

    def _resolve_competitions(
        self,
        config: AutomationRunConfig,
    ) -> tuple[CompetitionConfig, ...]:
        if config.leagues:
            resolved: list[CompetitionConfig] = []
            for league_id in config.leagues:
                league = self.reference.find_league_by_id(league_id, config.season)
                season = config.season or league.season
                resolved.append(
                    CompetitionConfig(
                        key=league.key,
                        league_id=league.league_id,
                        season=season,
                        name=league.name,
                        country=league.country,
                        enabled=True,
                        source="docs/api_football_reference.json",
                    )
                )
            return tuple(resolved)
        if self.competitions:
            return tuple(competition for competition in self.competitions if competition.enabled)
        return tuple(
            CompetitionConfig(
                key=league.key,
                league_id=league.league_id,
                season=league.season,
                name=league.name,
                country=league.country,
                enabled=True,
                source="docs/api_football_reference.json",
            )
            for league in self.reference.leagues()
        )

    def _refresh_fixtures(
        self,
        target_date: date,
        competitions: Sequence[CompetitionConfig],
        save_raw: bool,
    ) -> JsonDict:
        if self.api_client is None:
            raise PredictionError("refresh_data=True requires an API-Football client")
        service = FixtureIngestionService(self.session, self.api_client, save_raw=save_raw)
        payload: JsonDict = {"competitions": []}
        for competition in competitions:
            summary = service.ingest_date(
                target_date,
                league_id=competition.league_id,
                season=competition.season,
            )
            payload["competitions"].append(
                {
                    "league_id": competition.league_id,
                    "season": competition.season,
                    "summary": summary.as_dict(),
                }
            )
        return payload

    def _candidate_fixtures(
        self,
        target_date: date,
        competitions: Sequence[CompetitionConfig],
        local_timezone: ZoneInfo,
    ) -> list[models.Fixture]:
        self.session.flush()
        start_local = datetime.combine(target_date, time.min, tzinfo=local_timezone)
        end_local = start_local + timedelta(days=1)
        competition_filters = [
            (models.Fixture.league_id == competition.league_id)
            & (models.Fixture.season == competition.season)
            for competition in competitions
        ]
        stmt = select(models.Fixture).where(
            models.Fixture.date.is_not(None),
            models.Fixture.date >= start_local.astimezone(UTC),
            models.Fixture.date < end_local.astimezone(UTC),
        )
        if competition_filters:
            stmt = stmt.where(or_(*competition_filters))
        stmt = stmt.order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        return list(self.session.execute(stmt).scalars())

    def _prediction_service(self) -> PredictionServiceLike:
        if self.prediction_service_factory is not None:
            return self.prediction_service_factory(self.session)
        return PredictionService(
            self.reference,
            self.session,
            players_reference=self.players_reference,
        )

    def _predict_one(
        self,
        fixture: models.Fixture,
        prediction_service: PredictionServiceLike,
        *,
        config: AutomationRunConfig,
        prediction_time: datetime,
        run_key: str,
        target_date: date,
        window: PredictionWindow,
    ) -> AutomationFixtureResult:
        metadata = {
            "automation_window": window.value,
            "automation_date": target_date.isoformat(),
            "prediction_time": prediction_time.isoformat(),
            "run_key": run_key,
        }
        try:
            output = prediction_service.predict_fixture(
                fixture.fixture_id,
                prediction_time,
                model_dir=config.model_dir,
                refresh_data=config.refresh_data,
                save_raw=config.save_raw,
                api_client=self.api_client if config.refresh_data else None,
            )
            publication_decision = evaluate_publication(
                output.confidence_label,
                output.data_quality_json,
                min_data_quality_score=config.min_data_quality_score,
            )
            metadata.update(_publication_metadata(publication_decision))
            self._annotate_model_prediction(output.model_prediction_id, metadata)
            send_result = None
            status = "predicted"
            reason = None
            if config.send_discord:
                if (
                    not config.dry_run
                    and not config.print_only
                    and not publication_decision.allowed
                ):
                    status = "confidence_skipped"
                    reason = publication_decision.reason
                else:
                    duplicate = (
                        not config.force
                        and not config.dry_run
                        and not config.print_only
                        and self._already_sent(fixture.fixture_id, window, target_date)
                    )
                    if duplicate:
                        status = "duplicate_skipped"
                        reason = "discord_duplicate"
                    else:
                        send_result = self._send_discord(output, fixture, config, metadata)
                        status = "sent" if send_result.status == "sent" else send_result.status
            return AutomationFixtureResult(
                fixture_id=fixture.fixture_id,
                status=status,
                kickoff=fixture.date,
                league_id=fixture.league_id,
                season=fixture.season,
                reason=reason,
                predicted_result=output.predicted_result,
                model_prediction_id=output.model_prediction_id,
                discord_message_id=send_result.discord_message_id if send_result else None,
                probabilities=output.to_dict()["probabilities"],
            )
        except Exception as exc:
            return AutomationFixtureResult(
                fixture_id=fixture.fixture_id,
                status="failed",
                kickoff=fixture.date,
                league_id=fixture.league_id,
                season=fixture.season,
                error=str(exc),
            )

    def _send_discord(
        self,
        output: PredictionOutput,
        fixture: models.Fixture,
        config: AutomationRunConfig,
        metadata: JsonDict,
    ) -> DiscordSendResult:
        if self.discord_delivery is None:
            raise PredictionError("send_discord=True requires a DiscordDeliveryService")
        markdown = format_prediction_markdown(output, timezone_name=self.timezone_name)
        result = self.discord_delivery.send_markdown(
            markdown,
            league_id=fixture.league_id,
            season=fixture.season,
            channel_key="predictions",
            message_type="prediction",
            fixture_id=fixture.fixture_id,
            model_prediction_id=output.model_prediction_id,
            dry_run=config.dry_run,
            print_only=config.print_only,
            force=config.force,
        )
        if result.discord_message_id is not None:
            message = self.session.get(models.DiscordMessage, result.discord_message_id)
            if message is not None:
                payload = (
                    dict(message.payload_json) if isinstance(message.payload_json, dict) else {}
                )
                payload.update(metadata)
                message.payload_json = payload
        return result

    def _annotate_model_prediction(
        self,
        model_prediction_id: int | None,
        metadata: JsonDict,
    ) -> None:
        if model_prediction_id is None:
            return
        prediction = self.session.get(models.ModelPrediction, model_prediction_id)
        if prediction is None:
            return
        payload = dict(prediction.payload_json) if isinstance(prediction.payload_json, dict) else {}
        payload.update(metadata)
        prediction.payload_json = payload

    def _already_sent(
        self,
        fixture_id: int,
        window: PredictionWindow,
        target_date: date,
    ) -> bool:
        rows = self.session.execute(
            select(models.DiscordMessage).where(
                models.DiscordMessage.fixture_id == fixture_id,
                models.DiscordMessage.channel_key == "predictions",
                models.DiscordMessage.message_type == "prediction",
                models.DiscordMessage.status == "sent",
            )
        ).scalars()
        for row in rows:
            payload = row.payload_json if isinstance(row.payload_json, dict) else {}
            if (
                payload.get("automation_window") == window.value
                and payload.get("automation_date") == target_date.isoformat()
            ):
                return True
        return False


def _skip_reason(
    fixture: models.Fixture,
    prediction_time: datetime,
    target_date: date,
    window: PredictionWindow,
    local_timezone: ZoneInfo,
) -> str | None:
    if fixture.date is None:
        return "missing_kickoff"
    kickoff = ensure_aware_utc(fixture.date)
    local_date = kickoff.astimezone(local_timezone).date()
    if local_date != target_date:
        return "outside_date"
    if kickoff <= prediction_time:
        return "already_started"
    status_short = (fixture.status_short or fixture.status or "").upper()
    if status_short not in UPCOMING_STATUSES:
        return f"status_{status_short.lower() or 'unknown'}"
    if _window_matches(kickoff - prediction_time, window):
        return None
    return f"outside_{window.value}_window"


def _publication_metadata(decision: PublicationDecision) -> JsonDict:
    return publication_metadata(decision)


def _window_matches(delta: timedelta, window: PredictionWindow) -> bool:
    if window in {PredictionWindow.ALL, PredictionWindow.NOW}:
        return delta > timedelta(0)
    if window == PredictionWindow.LATE:
        return timedelta(0) < delta <= timedelta(minutes=30)
    if window == PredictionWindow.MID:
        return timedelta(minutes=60) < delta <= timedelta(hours=6)
    return delta > timedelta(hours=6)


def _skipped_result(fixture: models.Fixture, reason: str) -> AutomationFixtureResult:
    return AutomationFixtureResult(
        fixture_id=fixture.fixture_id,
        status="skipped",
        kickoff=fixture.date,
        league_id=fixture.league_id,
        season=fixture.season,
        reason=reason,
    )


def _run_key(
    target_date: date,
    window: PredictionWindow,
    competitions: Sequence[CompetitionConfig],
) -> str:
    league_part = ",".join(str(competition.league_id) for competition in competitions) or "all"
    return f"{target_date.isoformat()}:{window.value}:{league_part}"
