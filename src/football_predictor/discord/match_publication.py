"""Publish match analyses and post-match result summaries to Discord."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.discord.match_formatters import (
    format_match_analysis_message,
    format_match_result_message,
)
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.ingestion.fixtures import FixtureIngestionService
from football_predictor.prediction.service import PredictionService
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]
UPCOMING_STATUSES = {"", "NS", "TBD"}
FINISHED_STATUSES = {"FT", "AET", "PEN"}
ANALYSIS_WINDOW = "T-6"
ANALYSIS_OFFSET = timedelta(hours=6)


class ApiFootballPayloadClient(Protocol):
    def get_payload(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        save_raw: bool = False,
    ) -> Any:
        ...


@dataclass(frozen=True)
class MatchDiscordPublishResult:
    fixture_id: int
    channel_key: str
    message_type: str
    status: str
    model_prediction_id: int | None = None
    discord_message_id: int | None = None
    reason: str | None = None
    error: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "channel_key": self.channel_key,
            "message_type": self.message_type,
            "status": self.status,
            "model_prediction_id": self.model_prediction_id,
            "discord_message_id": self.discord_message_id,
            "reason": self.reason,
            "error": self.error,
        }


@dataclass(frozen=True)
class MatchDiscordPublishSummary:
    target_date: date
    message_type: str
    results: list[MatchDiscordPublishResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def sent(self) -> int:
        return sum(1 for result in self.results if result.status == "sent")

    @property
    def dry_run(self) -> int:
        return sum(1 for result in self.results if result.status == "dry_run")

    @property
    def print_only(self) -> int:
        return sum(1 for result in self.results if result.status == "print_only")

    @property
    def duplicate_skipped(self) -> int:
        return sum(1 for result in self.results if result.status == "duplicate_skipped")

    @property
    def skipped(self) -> int:
        return sum(1 for result in self.results if result.status == "skipped")

    @property
    def failed(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    def as_dict(self) -> JsonDict:
        return {
            "target_date": self.target_date.isoformat(),
            "message_type": self.message_type,
            "total": self.total,
            "sent": self.sent,
            "dry_run": self.dry_run,
            "print_only": self.print_only,
            "duplicate_skipped": self.duplicate_skipped,
            "skipped": self.skipped,
            "failed": self.failed,
            "results": [result.as_dict() for result in self.results],
        }


def publish_match_analyses(
    *,
    session: Session,
    competitions: Sequence[CompetitionConfig],
    delivery: DiscordDeliveryService,
    reference: ApiFootballReference,
    target_date: date,
    players_reference: PlayersReference | None = None,
    model_dir: Path | str | None = None,
    api_client: ApiFootballPayloadClient | None = None,
    refresh_data: bool = False,
    save_raw: bool = False,
    timezone_name: str = "Europe/Paris",
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    limit: int | None = None,
    now: datetime | None = None,
    analysis_grace_minutes: int = 15,
    echo: Callable[[str], None] | None = None,
) -> MatchDiscordPublishSummary:
    """Publish one due H-6 analysis per upcoming followed fixture."""
    current_time = ensure_aware_utc(now or utc_now())
    if refresh_data and api_client is None:
        raise PredictionError("refresh_data=True requires an API-Football client")
    if refresh_data and api_client is not None:
        _refresh_fixtures_for_date(
            session,
            api_client,
            target_date,
            competitions=competitions,
            save_raw=save_raw,
        )

    fixtures = _fixtures_for_date(
        session,
        competitions,
        target_date,
        timezone_name,
        statuses=UPCOMING_STATUSES,
    )
    service = PredictionService(
        reference,
        session,
        players_reference=players_reference,
    )
    results: list[MatchDiscordPublishResult] = []
    attempted = 0
    for fixture in fixtures:
        if fixture.date is None:
            continue
        kickoff = ensure_aware_utc(fixture.date)
        analysis_time = kickoff - ANALYSIS_OFFSET
        analysis_deadline = analysis_time + timedelta(minutes=max(0, analysis_grace_minutes))
        if not (analysis_time <= current_time <= analysis_deadline):
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="analyses",
                    message_type="analysis",
                    status="skipped",
                    reason="not_in_h6_grace_window",
                )
            )
            continue
        if limit is not None and attempted >= limit:
            break
        attempted += 1
        if not force and _already_sent(
            session,
            fixture.fixture_id,
            message_type="analysis",
            marker_key="analysis_window",
            marker_value=ANALYSIS_WINDOW,
        ):
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="analyses",
                    message_type="analysis",
                    status="duplicate_skipped",
                    reason="analysis_already_sent",
                )
            )
            continue
        try:
            prediction = _prediction_at_time(session, fixture.fixture_id, analysis_time)
            if prediction is None:
                output = service.predict_fixture(
                    fixture.fixture_id,
                    analysis_time,
                    model_dir=model_dir,
                    refresh_data=refresh_data,
                    save_raw=save_raw,
                    api_client=api_client,
                )
                prediction = session.get(models.ModelPrediction, output.model_prediction_id)
            if prediction is None:
                raise PredictionError("H-6 prediction was not persisted")
            snapshot = session.get(models.FeatureSnapshot, prediction.feature_snapshot_id)
            features = snapshot.features_json if snapshot is not None else {}
            markdown = format_match_analysis_message(
                fixture=fixture,
                prediction=prediction,
                features=features if isinstance(features, dict) else {},
                timezone_name=timezone_name,
            )
            if print_only and echo is not None:
                echo(markdown)
            send_result = delivery.send_markdown(
                markdown,
                competition_key=None,
                league_id=fixture.league_id,
                season=fixture.season,
                channel_key="analyses",
                message_type="analysis",
                fixture_id=fixture.fixture_id,
                model_prediction_id=prediction.id,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                wait=True,
            )
            _tag_discord_row(
                session,
                send_result.discord_message_id,
                {
                    "analysis_window": ANALYSIS_WINDOW,
                    "analysis_prediction_time": analysis_time.isoformat(),
                },
            )
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="analyses",
                    message_type="analysis",
                    status=send_result.status,
                    model_prediction_id=prediction.id,
                    discord_message_id=send_result.discord_message_id,
                )
            )
        except Exception as exc:
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="analyses",
                    message_type="analysis",
                    status="failed",
                    error=str(exc),
                )
            )
    return MatchDiscordPublishSummary(
        target_date=target_date,
        message_type="analysis",
        results=results,
    )


def publish_match_results(
    *,
    session: Session,
    competitions: Sequence[CompetitionConfig],
    delivery: DiscordDeliveryService,
    target_date: date,
    api_client: ApiFootballPayloadClient | None = None,
    refresh_data: bool = False,
    save_raw: bool = False,
    timezone_name: str = "Europe/Paris",
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    limit: int | None = None,
    echo: Callable[[str], None] | None = None,
) -> MatchDiscordPublishSummary:
    """Publish one post-match result summary per finished followed fixture."""
    if refresh_data and api_client is None:
        raise PredictionError("refresh_data=True requires an API-Football client")
    if refresh_data and api_client is not None:
        _refresh_fixtures_for_date(
            session,
            api_client,
            target_date,
            competitions=competitions,
            save_raw=save_raw,
        )

    fixtures = _fixtures_for_date(
        session,
        competitions,
        target_date,
        timezone_name,
        statuses=FINISHED_STATUSES,
    )
    results: list[MatchDiscordPublishResult] = []
    for fixture in fixtures:
        if limit is not None and len(results) >= limit:
            break
        if _goals_home(fixture) is None or _goals_away(fixture) is None:
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="resultats",
                    message_type="result",
                    status="skipped",
                    reason="missing_final_score",
                )
            )
            continue
        if not force and _already_sent(
            session,
            fixture.fixture_id,
            message_type="result",
            marker_key="result_publish",
            marker_value="final",
        ):
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="resultats",
                    message_type="result",
                    status="duplicate_skipped",
                    reason="result_already_sent",
                )
            )
            continue
        try:
            prediction = _published_prediction_before_match(session, fixture)
            markdown = format_match_result_message(
                fixture=fixture,
                prediction=prediction,
                timezone_name=timezone_name,
            )
            if print_only and echo is not None:
                echo(markdown)
            send_result = delivery.send_markdown(
                markdown,
                competition_key=None,
                league_id=fixture.league_id,
                season=fixture.season,
                channel_key="resultats",
                message_type="result",
                fixture_id=fixture.fixture_id,
                model_prediction_id=prediction.id if prediction is not None else None,
                dry_run=dry_run,
                print_only=print_only,
                force=force,
                wait=True,
            )
            _tag_discord_row(
                session,
                send_result.discord_message_id,
                {
                    "result_publish": "final",
                    "actual_outcome": _actual_outcome(fixture),
                },
            )
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="resultats",
                    message_type="result",
                    status=send_result.status,
                    model_prediction_id=prediction.id if prediction is not None else None,
                    discord_message_id=send_result.discord_message_id,
                )
            )
        except Exception as exc:
            results.append(
                MatchDiscordPublishResult(
                    fixture_id=fixture.fixture_id,
                    channel_key="resultats",
                    message_type="result",
                    status="failed",
                    error=str(exc),
                )
            )
    return MatchDiscordPublishSummary(
        target_date=target_date,
        message_type="result",
        results=results,
    )


def _fixtures_for_date(
    session: Session,
    competitions: Sequence[CompetitionConfig],
    target_date: date,
    timezone_name: str,
    *,
    statuses: set[str],
) -> list[models.Fixture]:
    enabled = [competition for competition in competitions if competition.enabled]
    if not enabled:
        return []
    start_utc, end_utc = _date_bounds(target_date, timezone_name)
    filters = [
        and_(
            models.Fixture.league_id == competition.league_id,
            models.Fixture.season == competition.season,
        )
        for competition in enabled
    ]
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.date.is_not(None),
            models.Fixture.date >= start_utc,
            models.Fixture.date < end_utc,
            or_(
                models.Fixture.status_short.in_(tuple(statuses)),
                models.Fixture.status.in_(tuple(statuses)),
            ),
            or_(*filters),
        )
        .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    )
    return list(session.execute(stmt).scalars())


def _refresh_fixtures_for_date(
    session: Session,
    api_client: ApiFootballPayloadClient,
    target_date: date,
    *,
    competitions: Sequence[CompetitionConfig],
    save_raw: bool,
) -> None:
    service = FixtureIngestionService(session, api_client, save_raw=save_raw)
    for competition in competitions:
        if not competition.enabled:
            continue
        service.ingest_date(
            target_date,
            league_id=competition.league_id,
            season=competition.season,
        )
    session.flush()


def _prediction_at_time(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> models.ModelPrediction | None:
    cutoff = ensure_aware_utc(prediction_time)
    return session.execute(
        select(models.ModelPrediction)
        .where(
            models.ModelPrediction.fixture_id == fixture_id,
            models.ModelPrediction.prediction_time == cutoff,
        )
        .order_by(models.ModelPrediction.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _published_prediction_before_match(
    session: Session,
    fixture: models.Fixture,
) -> models.ModelPrediction | None:
    cutoff = ensure_aware_utc(fixture.date) if fixture.date is not None else utc_now()
    published = session.execute(
        select(models.ModelPrediction)
        .join(
            models.DiscordMessage,
            models.DiscordMessage.model_prediction_id == models.ModelPrediction.id,
        )
        .where(
            models.ModelPrediction.fixture_id == fixture.fixture_id,
            models.ModelPrediction.prediction_time < cutoff,
            models.DiscordMessage.message_type == "prediction",
            models.DiscordMessage.status == "sent",
            models.DiscordMessage.dry_run.is_(False),
            models.DiscordMessage.print_only.is_(False),
        )
        .order_by(
            models.ModelPrediction.prediction_time.desc(),
            models.DiscordMessage.sent_at.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()
    if published is not None:
        return published
    return session.execute(
        select(models.ModelPrediction)
        .where(
            models.ModelPrediction.fixture_id == fixture.fixture_id,
            models.ModelPrediction.prediction_time < cutoff,
        )
        .order_by(models.ModelPrediction.prediction_time.desc())
        .limit(1)
    ).scalar_one_or_none()


def _already_sent(
    session: Session,
    fixture_id: int,
    *,
    message_type: str,
    marker_key: str,
    marker_value: str,
) -> bool:
    rows = session.execute(
        select(models.DiscordMessage).where(
            models.DiscordMessage.fixture_id == fixture_id,
            models.DiscordMessage.message_type == message_type,
            models.DiscordMessage.status == "sent",
            models.DiscordMessage.dry_run.is_(False),
            models.DiscordMessage.print_only.is_(False),
        )
    ).scalars()
    for row in rows:
        payload = row.payload_json if isinstance(row.payload_json, dict) else {}
        if payload.get(marker_key) == marker_value:
            return True
    return False


def _tag_discord_row(
    session: Session,
    discord_message_id: int | None,
    payload: JsonDict,
) -> None:
    if discord_message_id is None:
        return
    row = session.get(models.DiscordMessage, discord_message_id)
    if row is None:
        return
    current = row.payload_json if isinstance(row.payload_json, dict) else {}
    row.payload_json = {**current, **payload}
    session.flush()


def _date_bounds(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    start_local = datetime.combine(target_date, time.min, tzinfo=timezone)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _goals_home(fixture: models.Fixture) -> int | None:
    return fixture.home_goals if fixture.home_goals is not None else fixture.goals_home


def _goals_away(fixture: models.Fixture) -> int | None:
    return fixture.away_goals if fixture.away_goals is not None else fixture.goals_away


def _actual_outcome(fixture: models.Fixture) -> str | None:
    home = _goals_home(fixture)
    away = _goals_away(fixture)
    if home is None or away is None:
        return None
    if home > away:
        return "HOME"
    if home < away:
        return "AWAY"
    return "DRAW"
