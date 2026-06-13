"""Daily World Cup prediction runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.prediction.draw_safety import draw_safety_skip_reason
from football_predictor.prediction.publication_policy import (
    CONFIDENCE_SKIP_REASON,
    is_publishable_confidence,
)
from football_predictor.prediction.scheduler import (
    DailyPredictionWindow,
    fixture_matches_window,
    parse_daily_window,
    prediction_time_for_fixture,
)
from football_predictor.prediction.service import ApiFootballPayloadClient
from football_predictor.prediction.staff_publication import send_skipped_prediction_to_staff
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.security.sanitize import sanitize_text
from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.logging import get_logger
from football_predictor.worldcup.references import WorldCupReferenceBundle
from football_predictor.worldcup.service import (
    WORLD_CUP_LEAGUE_ID,
    WORLD_CUP_SEASON,
    WorldCupPredictionService,
)

JsonDict = dict[str, Any]
UPCOMING_STATUSES = {"", "NS", "TBD"}
logger = get_logger(__name__)
_LIVE_WINDOWS = {
    DailyPredictionWindow.LATE,
    DailyPredictionWindow.NOW,
    DailyPredictionWindow.ALL,
}


@dataclass(frozen=True)
class WorldCupDailyResult:
    fixture_id: int
    status: str
    kickoff: datetime | None = None
    prediction_time: datetime | None = None
    confidence_label: str | None = None
    confidence_score: float | None = None
    model_prediction_id: int | None = None
    discord_message_id: int | None = None
    reason: str | None = None
    error: str | None = None
    source_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "status": self.status,
            "kickoff": self.kickoff.isoformat() if self.kickoff else None,
            "prediction_time": self.prediction_time.isoformat() if self.prediction_time else None,
            "confidence_label": self.confidence_label,
            "confidence_score": self.confidence_score,
            "model_prediction_id": self.model_prediction_id,
            "discord_message_id": self.discord_message_id,
            "reason": self.reason,
            "error": self.error,
            "source_warnings": self.source_warnings,
        }


@dataclass(frozen=True)
class WorldCupDailySummary:
    target_date: date
    window: DailyPredictionWindow
    send_discord: bool
    refresh_data: bool = False
    results: list[WorldCupDailyResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def sent(self) -> int:
        return sum(1 for row in self.results if row.status == "sent")

    @property
    def confidence_skipped(self) -> int:
        return sum(1 for row in self.results if row.status == "confidence_skipped")

    @property
    def failed(self) -> int:
        return sum(1 for row in self.results if row.status == "failed")

    def as_dict(self) -> JsonDict:
        return {
            "target_date": self.target_date.isoformat(),
            "window": self.window.value,
            "mode": "worldcup_1x2",
            "league_id": WORLD_CUP_LEAGUE_ID,
            "season": WORLD_CUP_SEASON,
            "send_discord": self.send_discord,
            "refresh_data": self.refresh_data,
            "total": self.total,
            "success": self.total - self.failed,
            "failed": self.failed,
            "sent": self.sent,
            "confidence_skipped": self.confidence_skipped,
            "results": [row.as_dict() for row in self.results],
        }


def run_daily_worldcup_predictions(
    session: Session,
    bundle: WorldCupReferenceBundle,
    *,
    target_date: date,
    window: DailyPredictionWindow | str = DailyPredictionWindow.LATE,
    model_dir: Path | str | None = Path("data/models/worldcup-1x2"),
    delivery: DiscordDeliveryService | None = None,
    send_discord: bool = False,
    refresh_data: bool = False,
    api_client: ApiFootballPayloadClient | None = None,
    reference: ApiFootballReference | None = None,
    players_reference: PlayersReference | None = None,
    save_raw: bool = False,
    dry_run: bool = True,
    print_only: bool = False,
    force: bool = False,
    timezone_name: str = "Europe/Paris",
    now: datetime | None = None,
    limit: int | None = None,
) -> WorldCupDailySummary:
    resolved_window = parse_daily_window(window)
    if refresh_data and api_client is None:
        raise PredictionError("refresh_data=True requires an API-Football client")
    current_time = _current_time(now)
    fixtures = (
        _fixtures_for_late_window(session, current_time)
        if resolved_window == DailyPredictionWindow.LATE
        else _fixtures_for_date(session, target_date, timezone_name=timezone_name)
    )
    fixtures = [
        fixture
        for fixture in fixtures
        if fixture_matches_window(fixture.date, resolved_window, now=current_time)
    ]
    if limit is not None:
        fixtures = fixtures[:limit]
    service = WorldCupPredictionService(
        session,
        bundle,
        model_dir=model_dir,
        reference=reference,
        players_reference=players_reference,
    )
    results: list[WorldCupDailyResult] = []
    for fixture in fixtures:
        try:
            if fixture.date is None:
                continue
            prediction_time = prediction_time_for_fixture(
                fixture.date,
                resolved_window,
                now=current_time,
            )
            service_prediction_time = (
                None if refresh_data and resolved_window in _LIVE_WINDOWS else prediction_time
            )
            output = service.predict_fixture(
                fixture.fixture_id,
                service_prediction_time,
                refresh_data=refresh_data,
                save_raw=save_raw,
                api_client=api_client,
            )
            if not send_discord:
                results.append(_result(output, "predicted", fixture=fixture))
                continue
            markdown = format_prediction_markdown(output, timezone_name=timezone_name)
            draw_safety_reason = draw_safety_skip_reason(output.draw_safety_json)
            data_quality_reason = _worldcup_data_quality_skip_reason(output.data_quality_json)
            if (
                draw_safety_reason is None
                and data_quality_reason is None
                and is_publishable_confidence(output.confidence_label)
            ):
                send_result = delivery.send_markdown(
                    markdown,
                    competition_key="fifa_world_cup_2026",
                    league_id=WORLD_CUP_LEAGUE_ID,
                    season=WORLD_CUP_SEASON,
                    channel_key="predictions",
                    message_type="prediction",
                    fixture_id=fixture.fixture_id,
                    model_prediction_id=output.model_prediction_id,
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    payload_metadata={
                        "model_family": "worldcup_1x2",
                        "daily_window": resolved_window.value,
                        "automation_window": resolved_window.value,
                        "automation_date": target_date.isoformat(),
                        "prediction_time": output.prediction_time.isoformat()
                        if output.prediction_time
                        else None,
                        "draw_safety": output.draw_safety_json,
                        "source_health": output.data_quality_json.get("source_health"),
                        "worldcup_fixture_quality": output.data_quality_json.get(
                            "worldcup_fixture_quality"
                        ),
                    },
                ) if delivery is not None else None
                status = send_result.status if send_result is not None else "predicted"
                message_id = send_result.discord_message_id if send_result is not None else None
                results.append(
                    _result(
                        output,
                        status,
                        fixture=fixture,
                        discord_message_id=message_id,
                    )
                )
            else:
                skip_reason = draw_safety_reason or data_quality_reason or CONFIDENCE_SKIP_REASON
                if not dry_run and not print_only:
                    send_skipped_prediction_to_staff(
                        delivery,
                        markdown,
                        fixture=fixture,
                        model_family="worldcup_1x2",
                        confidence_label=output.confidence_label,
                        confidence_score=output.confidence_score,
                        reason=skip_reason,
                        prediction_time=output.prediction_time,
                        automation_window=resolved_window.value,
                        model_prediction_id=output.model_prediction_id,
                        payload_metadata={
                            "draw_safety": output.draw_safety_json,
                            "source_health": output.data_quality_json.get("source_health"),
                            "worldcup_fixture_quality": output.data_quality_json.get(
                                "worldcup_fixture_quality"
                            ),
                        },
                        force=force,
                    )
                results.append(
                    _result(
                        output,
                        "confidence_skipped",
                        fixture=fixture,
                        reason=skip_reason,
                    )
                )
        except Exception as exc:
            logger.exception(
                "Unexpected World Cup daily prediction failure fixture_id=%s error=%s",
                fixture.fixture_id,
                sanitize_text(str(exc)),
            )
            results.append(
                WorldCupDailyResult(
                    fixture_id=fixture.fixture_id,
                    status="failed",
                    kickoff=fixture.date,
                    error=str(exc),
                )
            )
    return WorldCupDailySummary(
        target_date=target_date,
        window=resolved_window,
        send_discord=send_discord,
        refresh_data=refresh_data,
        results=results,
    )


def _fixtures_for_date(
    session: Session,
    target_date: date,
    *,
    timezone_name: str,
) -> list[models.Fixture]:
    local_timezone = ZoneInfo(timezone_name)
    start_local = datetime.combine(target_date, time.min, tzinfo=local_timezone)
    end_local = start_local + timedelta(days=1)
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.league_id == WORLD_CUP_LEAGUE_ID,
            models.Fixture.season == WORLD_CUP_SEASON,
            models.Fixture.date >= start_local.astimezone(UTC),
            models.Fixture.date < end_local.astimezone(UTC),
            or_(
                models.Fixture.status_short.in_(tuple(UPCOMING_STATUSES)),
                models.Fixture.status.in_(tuple(UPCOMING_STATUSES)),
            ),
        )
        .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    )
    return list(session.execute(stmt).scalars())


def _fixtures_for_late_window(
    session: Session,
    now: datetime,
) -> list[models.Fixture]:
    current_time = _current_time(now)
    late_end = current_time + timedelta(minutes=30)
    stmt = (
        select(models.Fixture)
        .where(
            models.Fixture.league_id == WORLD_CUP_LEAGUE_ID,
            models.Fixture.season == WORLD_CUP_SEASON,
            models.Fixture.date.is_not(None),
            models.Fixture.date >= current_time,
            models.Fixture.date <= late_end,
            or_(
                models.Fixture.status_short.in_(tuple(UPCOMING_STATUSES)),
                models.Fixture.status.in_(tuple(UPCOMING_STATUSES)),
            ),
        )
        .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    )
    return list(session.execute(stmt).scalars())


def _current_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _result(
    output: Any,
    status: str,
    *,
    fixture: models.Fixture,
    discord_message_id: int | None = None,
    reason: str | None = None,
) -> WorldCupDailyResult:
    return WorldCupDailyResult(
        fixture_id=fixture.fixture_id,
        status=status,
        kickoff=fixture.date,
        prediction_time=output.prediction_time,
        confidence_label=output.confidence_label,
        confidence_score=output.confidence_score,
        model_prediction_id=output.model_prediction_id,
        discord_message_id=discord_message_id,
        reason=reason,
        source_warnings=_source_warnings(output.data_quality_json),
    )


def _worldcup_data_quality_skip_reason(data_quality: JsonDict | None) -> str | None:
    if not isinstance(data_quality, dict):
        return None
    score = data_quality.get("worldcup_fixture_quality_score")
    try:
        if score is not None and float(score) < 55.0:
            return "worldcup_data_quality_low"
    except (TypeError, ValueError):
        return None
    warnings = set(data_quality.get("warnings") or [])
    if "lineups_expected_missing" in warnings:
        return "worldcup_lineups_expected_missing"
    return None


def _source_warnings(data_quality: JsonDict | None) -> list[str]:
    if not isinstance(data_quality, dict):
        return []
    warnings = data_quality.get("warnings") or []
    return sorted(
        {
            str(warning)
            for warning in warnings
            if str(warning).endswith("_failed")
            or str(warning).endswith("_failed_close_to_kickoff")
        }
    )
