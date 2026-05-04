"""Daily fixture prediction runner.

This module is intentionally dependency-injectable: tests and local dry-runs can
provide a SQLite session, fake API client, fake prediction service, and fake
Discord delivery service without any network access.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
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
from football_predictor.ingestion.ingest_match_details import FixtureDetailsIngestionService
from football_predictor.ingestion.ingest_odds import OddsIngestionService
from football_predictor.prediction.scheduler import (
    DailyPredictionWindow,
    daily_run_key,
    fixture_matches_window,
    parse_daily_window,
    prediction_time_for_fixture,
)
from football_predictor.prediction.service import (
    ApiFootballPayloadClient,
    PredictionOutput,
    PredictionService,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.time import ensure_aware_utc, utc_now

UPCOMING_STATUSES = {"", "NS", "TBD"}
JsonDict = dict[str, Any]


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


@dataclass(frozen=True)
class DailyFixtureResult:
    fixture_id: int
    status: str
    kickoff: datetime | None = None
    prediction_time: datetime | None = None
    league_id: int | None = None
    season: int | None = None
    model_prediction_id: int | None = None
    discord_message_id: int | None = None
    reason: str | None = None
    error: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "status": self.status,
            "kickoff": self.kickoff.isoformat() if self.kickoff else None,
            "prediction_time": self.prediction_time.isoformat()
            if self.prediction_time
            else None,
            "league_id": self.league_id,
            "season": self.season,
            "model_prediction_id": self.model_prediction_id,
            "discord_message_id": self.discord_message_id,
            "reason": self.reason,
            "error": self.error,
        }


@dataclass(frozen=True)
class DailyPredictionSummary:
    target_date: date
    window: DailyPredictionWindow
    run_key: str
    league_ids: tuple[int, ...]
    season: int | None
    refresh_data: bool
    send_discord: bool
    results: list[DailyFixtureResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def found(self) -> int:
        return self.total

    @property
    def success(self) -> int:
        return sum(
            1
            for result in self.results
            if result.status in {"predicted", "sent", "dry_run", "print_only"}
        )

    @property
    def predicted(self) -> int:
        return self.success

    @property
    def failed(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    @property
    def sent(self) -> int:
        return sum(1 for result in self.results if result.status == "sent")

    @property
    def skipped(self) -> int:
        return sum(
            1
            for result in self.results
            if result.status in {"skipped", "duplicate_skipped"}
        )

    @property
    def duplicate_skipped(self) -> int:
        return sum(1 for result in self.results if result.status == "duplicate_skipped")

    def as_dict(self) -> JsonDict:
        return {
            "target_date": self.target_date.isoformat(),
            "window": self.window.value,
            "run_key": self.run_key,
            "league_ids": list(self.league_ids),
            "leagues": list(self.league_ids),
            "season": self.season,
            "refresh_data": self.refresh_data,
            "send_discord": self.send_discord,
            "total": self.total,
            "found": self.total,
            "success": self.success,
            "predicted": self.success,
            "failed": self.failed,
            "sent": self.sent,
            "skipped": self.skipped,
            "duplicate_skipped": self.duplicate_skipped,
            "results": [result.as_dict() for result in self.results],
        }


def get_fixtures_to_predict(
    fixture_date: date,
    league_ids: Sequence[int] | None = None,
    season: int | None = None,
    *,
    session: Session,
    competitions: Sequence[CompetitionConfig] = (),
    reference: ApiFootballReference | None = None,
    timezone_name: str = "Europe/Paris",
) -> list[models.Fixture]:
    """Return not-started fixtures for a local date, optionally filtered by league."""
    explicit_leagues = tuple(league_ids or ())
    enabled_competitions = tuple(competition for competition in competitions if competition.enabled)
    resolved_leagues = explicit_leagues or _enabled_competition_leagues(enabled_competitions)
    if competitions and not resolved_leagues:
        return []
    if reference is not None:
        for league_id in resolved_leagues:
            if league_id > 0:
                _find_reference_league(reference, league_id, season)

    local_timezone = ZoneInfo(timezone_name)
    start_local = datetime.combine(fixture_date, time.min, tzinfo=local_timezone)
    end_local = start_local + timedelta(days=1)
    session.flush()
    stmt = select(models.Fixture).where(
        models.Fixture.date.is_not(None),
        models.Fixture.date >= start_local.astimezone(UTC),
        models.Fixture.date < end_local.astimezone(UTC),
        or_(
            models.Fixture.status_short.in_(tuple(UPCOMING_STATUSES)),
            models.Fixture.status.in_(tuple(UPCOMING_STATUSES)),
        ),
    )
    if season is not None:
        stmt = stmt.where(models.Fixture.season == season)
    if explicit_leagues:
        stmt = stmt.where(models.Fixture.league_id.in_(resolved_leagues))
    elif enabled_competitions:
        filters = [
            (models.Fixture.league_id == competition.league_id)
            & (models.Fixture.season == competition.season)
            for competition in enabled_competitions
        ]
        if filters:
            stmt = stmt.where(or_(*filters))
    stmt = stmt.order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    return list(session.execute(stmt).scalars())


def run_daily_predictions(
    fixture_date: date | None = None,
    league_ids: Sequence[int] | None = None,
    window: DailyPredictionWindow | str = DailyPredictionWindow.NOW,
    send_discord: bool = False,
    refresh_data: bool = True,
    dry_run: bool = False,
    *,
    session: Session,
    reference: ApiFootballReference,
    players_reference: PlayersReference | None = None,
    competitions: Sequence[CompetitionConfig] = (),
    season: int | None = None,
    model_dir: Path | str | None = None,
    api_client: ApiFootballPayloadClient | None = None,
    discord_delivery: DiscordDeliveryService | None = None,
    prediction_service_factory: PredictionServiceFactory | None = None,
    timezone_name: str = "Europe/Paris",
    force: bool = False,
    print_only: bool = False,
    save_raw: bool = False,
    limit: int | None = None,
    now: datetime | None = None,
) -> DailyPredictionSummary:
    """Predict all eligible fixtures for a date and return a compact summary."""
    resolved_window = parse_daily_window(window)
    current_time = ensure_aware_utc(now or utc_now())
    local_timezone = ZoneInfo(timezone_name)
    target_date = fixture_date or current_time.astimezone(local_timezone).date()
    resolved_leagues = tuple(league_ids or _enabled_competition_leagues(competitions))
    run_key = daily_run_key(target_date.isoformat(), resolved_window, resolved_leagues, season)

    if refresh_data and api_client is None:
        raise PredictionError("refresh_data=True requires an API-Football client")
    if send_discord and discord_delivery is None:
        raise PredictionError("send_discord=True requires a DiscordDeliveryService")

    if refresh_data and api_client is not None:
        _refresh_fixtures_for_date(
            session,
            api_client,
            target_date,
            league_ids=resolved_leagues,
            season=season,
            competitions=competitions,
            reference=reference,
            save_raw=save_raw,
        )

    fixtures = get_fixtures_to_predict(
        target_date,
        resolved_leagues or None,
        season,
        session=session,
        competitions=competitions,
        reference=reference if resolved_leagues else None,
        timezone_name=timezone_name,
    )
    fixtures = [
        fixture
        for fixture in fixtures
        if fixture_matches_window(fixture.date, resolved_window, current_time)
    ]
    if limit is not None:
        fixtures = fixtures[:limit]

    prediction_service = _prediction_service(
        session,
        reference,
        players_reference,
        prediction_service_factory,
    )
    results: list[DailyFixtureResult] = []
    for fixture in fixtures:
        prediction_time = prediction_time_for_fixture(
            fixture.date or current_time,
            resolved_window,
            now=current_time,
        )
        try:
            if (
                send_discord
                and not dry_run
                and not print_only
                and not force
                and _has_sent_prediction_window(session, fixture.fixture_id, resolved_window)
            ):
                results.append(
                    _result(
                        fixture,
                        "duplicate_skipped",
                        prediction_time,
                        reason="sent_prediction_window",
                    )
                )
                continue
            refresh_warnings: list[str] = []
            if refresh_data and api_client is not None:
                refresh_warnings = _refresh_fixture_inputs(
                    session,
                    fixture,
                    api_client,
                    reference=reference,
                    players_reference=players_reference,
                    window=resolved_window,
                    save_raw=save_raw,
                )
                if _uses_live_prediction_time(resolved_window):
                    prediction_time = prediction_time_for_fixture(
                        fixture.date or utc_now(),
                        resolved_window,
                        now=utc_now(),
                    )
            output = prediction_service.predict_fixture(
                fixture.fixture_id,
                prediction_time,
                model_dir=model_dir,
                refresh_data=False,
                save_raw=save_raw,
            )
            metadata = {
                "daily_window": resolved_window.value,
                "automation_window": resolved_window.value,
                "automation_date": target_date.isoformat(),
                "prediction_time": prediction_time.isoformat(),
                "run_key": run_key,
                "refresh_warnings": refresh_warnings,
            }
            _annotate_model_prediction(session, output.model_prediction_id, metadata)
            if send_discord:
                send_result = _send_prediction(
                    discord_delivery,
                    output,
                    fixture,
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    metadata=metadata,
                )
                results.append(
                    _result(
                        fixture,
                        send_result.status,
                        prediction_time,
                        model_prediction_id=output.model_prediction_id,
                        discord_message_id=send_result.discord_message_id,
                    )
                )
            else:
                results.append(
                    _result(
                        fixture,
                        "predicted",
                        prediction_time,
                        model_prediction_id=output.model_prediction_id,
                    )
                )
        except Exception as exc:
            results.append(_result(fixture, "failed", prediction_time, error=str(exc)))

    return DailyPredictionSummary(
        target_date=target_date,
        window=resolved_window,
        run_key=run_key,
        league_ids=resolved_leagues,
        season=season,
        refresh_data=refresh_data,
        send_discord=send_discord,
        results=results,
    )


def _uses_live_prediction_time(window: DailyPredictionWindow) -> bool:
    return window in {
        DailyPredictionWindow.LATE,
        DailyPredictionWindow.NOW,
        DailyPredictionWindow.ALL,
    }


def _prediction_service(
    session: Session,
    reference: ApiFootballReference,
    players_reference: PlayersReference | None,
    factory: PredictionServiceFactory | None,
) -> PredictionServiceLike:
    if factory is not None:
        return factory(session)
    return PredictionService(reference, session, players_reference=players_reference)


def _refresh_fixtures_for_date(
    session: Session,
    api_client: ApiFootballPayloadClient,
    target_date: date,
    *,
    league_ids: tuple[int, ...],
    season: int | None,
    competitions: Sequence[CompetitionConfig],
    reference: ApiFootballReference,
    save_raw: bool,
) -> None:
    service = FixtureIngestionService(session, api_client, save_raw=save_raw)
    if league_ids:
        for league_id in league_ids:
            resolved_season = season
            if resolved_season is None and league_id > 0:
                resolved_season = _find_reference_league(reference, league_id, None).season
            service.ingest_date(target_date, league_id=league_id, season=resolved_season)
        return
    enabled = [competition for competition in competitions if competition.enabled]
    if enabled:
        for competition in enabled:
            service.ingest_date(
                target_date,
                league_id=competition.league_id,
                season=competition.season,
            )
        return
    service.ingest_date(target_date)


def _refresh_fixture_inputs(
    session: Session,
    fixture: models.Fixture,
    api_client: ApiFootballPayloadClient,
    *,
    reference: ApiFootballReference,
    players_reference: PlayersReference | None,
    window: DailyPredictionWindow,
    save_raw: bool,
) -> list[str]:
    warnings: list[str] = []
    _safe_refresh(
        warnings,
        "fixture",
        lambda: FixtureIngestionService(
            session,
            api_client,
            save_raw=save_raw,
        ).ingest_fixture_by_id(
            fixture.fixture_id,
        ),
    )
    _safe_refresh(
        warnings,
        "odds",
        lambda: OddsIngestionService(
            session,
            api_client,
            reference=reference,
            save_raw=save_raw,
        ).ingest_odds_for_fixture(fixture.fixture_id),
    )
    details = FixtureDetailsIngestionService(
        session,
        api_client,
        reference=reference,
        players_reference=players_reference,
        save_raw=save_raw,
    )
    _safe_refresh(
        warnings,
        "injuries",
        lambda: details.ingest_injuries_for_fixture(fixture.fixture_id),
    )
    _safe_refresh(
        warnings,
        "api_prediction",
        lambda: details.ingest_api_prediction(fixture.fixture_id),
    )
    if window == DailyPredictionWindow.LATE:
        _safe_refresh(
            warnings,
            "lineups",
            lambda: details.ingest_fixture_lineups(fixture.fixture_id),
        )
    session.flush()
    return warnings


def _safe_refresh(warnings: list[str], label: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception as exc:
        warnings.append(f"{label}: {exc}")


def _send_prediction(
    delivery: DiscordDeliveryService | None,
    output: PredictionOutput,
    fixture: models.Fixture,
    *,
    dry_run: bool,
    print_only: bool,
    force: bool,
    metadata: JsonDict,
) -> DiscordSendResult:
    if delivery is None:
        raise PredictionError("send_discord=True requires a DiscordDeliveryService")
    result = delivery.send_markdown(
        format_prediction_markdown(output),
        league_id=fixture.league_id,
        season=fixture.season,
        channel_key="predictions",
        message_type="prediction",
        fixture_id=fixture.fixture_id,
        model_prediction_id=output.model_prediction_id,
        dry_run=dry_run,
        print_only=print_only,
        force=force,
    )
    if result.discord_message_id is not None:
        message = delivery.session.get(models.DiscordMessage, result.discord_message_id)
        if message is not None:
            payload = dict(message.payload_json) if isinstance(message.payload_json, dict) else {}
            payload.update(metadata)
            message.payload_json = payload
    return result


def _annotate_model_prediction(
    session: Session,
    model_prediction_id: int | None,
    metadata: JsonDict,
) -> None:
    if model_prediction_id is None:
        return
    prediction = session.get(models.ModelPrediction, model_prediction_id)
    if prediction is None:
        return
    payload = dict(prediction.payload_json) if isinstance(prediction.payload_json, dict) else {}
    payload.update(metadata)
    prediction.payload_json = payload
    session.flush()


def _has_sent_prediction_window(
    session: Session,
    fixture_id: int,
    window: DailyPredictionWindow,
) -> bool:
    rows = session.execute(
        select(models.DiscordMessage).where(
            models.DiscordMessage.fixture_id == fixture_id,
            models.DiscordMessage.message_type == "prediction",
            models.DiscordMessage.status == "sent",
            models.DiscordMessage.dry_run.is_(False),
            models.DiscordMessage.print_only.is_(False),
        )
    ).scalars()
    for row in rows:
        payload = row.payload_json if isinstance(row.payload_json, dict) else {}
        if (
            payload.get("daily_window") == window.value
            or payload.get("automation_window") == window.value
        ):
            return True
    return False


def _result(
    fixture: models.Fixture,
    status: str,
    prediction_time: datetime,
    *,
    model_prediction_id: int | None = None,
    discord_message_id: int | None = None,
    reason: str | None = None,
    error: str | None = None,
) -> DailyFixtureResult:
    return DailyFixtureResult(
        fixture_id=fixture.fixture_id,
        status=status,
        kickoff=fixture.date,
        prediction_time=prediction_time,
        league_id=fixture.league_id,
        season=fixture.season,
        model_prediction_id=model_prediction_id,
        discord_message_id=discord_message_id,
        reason=reason,
        error=error,
    )


def _enabled_competition_leagues(competitions: Sequence[CompetitionConfig]) -> tuple[int, ...]:
    return tuple(competition.league_id for competition in competitions if competition.enabled)


def _find_reference_league(
    reference: ApiFootballReference,
    league_id: int,
    season: int | None,
) -> Any:
    if season is not None:
        return reference.find_league_by_id(league_id, season)
    matches = [league for league in reference.leagues() if league.league_id == league_id]
    if not matches:
        return reference.find_league_by_id(league_id, season)
    return matches[0]
