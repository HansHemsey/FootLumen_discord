"""Daily O/U 2.5 prediction runner.

Mirrors the structure of prediction/run_daily.py — dependency-injectable so
tests and local dry-runs need no network access.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.ou_model.discord.ou_formatter import format_ou_prediction_markdown
from football_predictor.ou_model.prediction.ou_service import (
    OUPredictionOutput,
    OUPredictionService,
)
from football_predictor.prediction.publication_policy import (
    CONFIDENCE_SKIP_REASON,
    is_publishable_confidence,
    normalize_confidence_label,
)
from football_predictor.prediction.scheduler import (
    DailyPredictionWindow,
    fixture_matches_window,
    parse_daily_window,
    prediction_time_for_fixture,
)
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.time import ensure_aware_utc, utc_now

UPCOMING_STATUSES = {"", "NS", "TBD"}
JsonDict = dict[str, Any]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OUDailyFixtureResult:
    fixture_id: int
    status: str
    kickoff: datetime | None = None
    prediction_time: datetime | None = None
    league_id: int | None = None
    p_over: float | None = None
    p_under: float | None = None
    edge_over: float | None = None
    confidence_label: str | None = None
    confidence_score: float | None = None
    ou_model_prediction_id: int | None = None
    discord_message_id: int | None = None
    discord_sent: bool = False
    reason: str | None = None
    error: str | None = None

    def as_dict(self) -> JsonDict:
        return {
            "fixture_id": self.fixture_id,
            "status": self.status,
            "kickoff": self.kickoff.isoformat() if self.kickoff else None,
            "prediction_time": self.prediction_time.isoformat() if self.prediction_time else None,
            "league_id": self.league_id,
            "p_over": self.p_over,
            "p_under": self.p_under,
            "edge_over": self.edge_over,
            "confidence_label": self.confidence_label,
            "confidence_score": self.confidence_score,
            "ou_model_prediction_id": self.ou_model_prediction_id,
            "discord_message_id": self.discord_message_id,
            "discord_sent": self.discord_sent,
            "reason": self.reason,
            "error": self.error,
        }


@dataclass(frozen=True)
class OUDailyPredictionSummary:
    target_date: date
    window: DailyPredictionWindow
    results: list[OUDailyFixtureResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success(self) -> int:
        return sum(
            1
            for r in self.results
            if r.status in {"predicted", "sent", "dry_run", "print_only", "confidence_skipped"}
        )

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    @property
    def sent(self) -> int:
        return sum(1 for r in self.results if r.discord_sent)

    @property
    def confidence_skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "confidence_skipped")

    def as_dict(self) -> JsonDict:
        return {
            "target_date": self.target_date.isoformat(),
            "window": self.window.value,
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "sent": self.sent,
            "confidence_skipped": self.confidence_skipped,
            "results": [r.as_dict() for r in self.results],
        }


def _get_fixtures_for_date(
    session: Session,
    fixture_date: date,
    *,
    league_ids: Sequence[int] | None = None,
    season: int | None = None,
    timezone_name: str = "Europe/Paris",
) -> list[models.Fixture]:
    local_tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(fixture_date, time.min, tzinfo=local_tz)
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
    if league_ids:
        stmt = stmt.where(models.Fixture.league_id.in_(tuple(league_ids)))
    stmt = stmt.order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    return list(session.execute(stmt).scalars())


def run_daily_ou_predictions(
    fixture_date: date | None = None,
    *,
    session: Session,
    ou_service: OUPredictionService | None = None,
    discord_delivery: DiscordDeliveryService | None = None,
    league_ids: Sequence[int] | None = None,
    season: int | None = None,
    model_dir: Path | str | None = None,
    ou_bet_id: int | None = None,
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
    send_discord: bool = False,
    dry_run: bool = False,
    print_only: bool = False,
    window: DailyPredictionWindow | str = DailyPredictionWindow.LATE,
    timezone_name: str = "Europe/Paris",
    now: datetime | None = None,
    limit: int | None = None,
    edge_threshold: float = 0.02,
) -> OUDailyPredictionSummary:
    """Predict O/U 2.5 for all eligible fixtures on a date."""
    resolved_window = parse_daily_window(window)
    current_time = ensure_aware_utc(now or utc_now())
    local_tz = ZoneInfo(timezone_name)
    target_date = fixture_date or current_time.astimezone(local_tz).date()

    if send_discord and discord_delivery is None:
        raise ValueError("send_discord=True requires a DiscordDeliveryService")

    resolved_service = ou_service or OUPredictionService(
        session,
        model_dir=model_dir,
        ou_bet_id=ou_bet_id,
        players_reference=players_reference,
        api_reference=api_reference,
    )

    fixtures = _get_fixtures_for_date(
        session,
        target_date,
        league_ids=league_ids,
        season=season,
        timezone_name=timezone_name,
    )
    fixtures = [
        fixture
        for fixture in fixtures
        if fixture_matches_window(fixture.date, resolved_window, current_time)
    ]
    if limit is not None:
        fixtures = fixtures[:limit]

    logger.info(
        "O/U daily run: %d fixtures for %s window=%s",
        len(fixtures),
        target_date,
        resolved_window.value,
    )

    results: list[OUDailyFixtureResult] = []
    for fixture in fixtures:
        prediction_time = prediction_time_for_fixture(
            fixture.date or current_time,
            resolved_window,
            now=current_time,
        )
        discord_sent = False
        discord_message_id: int | None = None
        reason: str | None = None
        try:
            prediction: OUPredictionOutput = resolved_service.predict_fixture_ou(
                fixture.fixture_id,
                prediction_time,
                save_to_db=not dry_run,
            )

            status = "predicted"
            if send_discord and discord_delivery is not None:
                if (
                    not dry_run
                    and not print_only
                    and not is_publishable_confidence(prediction.confidence_label)
                ):
                    logger.info(
                        "O/U Discord publication skipped: fixture_id=%s "
                        "confidence_label=%s confidence_score=%s expected=%s "
                        "window=%s",
                        fixture.fixture_id,
                        normalize_confidence_label(prediction.confidence_label),
                        prediction.confidence_score,
                        "High|Very High",
                        resolved_window.value,
                    )
                    status = "confidence_skipped"
                    reason = CONFIDENCE_SKIP_REASON
                else:
                    try:
                        md = format_ou_prediction_markdown(
                            prediction,
                            fixture,
                            timezone_name=timezone_name,
                            edge_display_threshold=edge_threshold,
                        )
                        if print_only:
                            print(md)
                        send_result = discord_delivery.send_markdown(
                            md,
                            league_id=fixture.league_id,
                            season=fixture.season,
                            channel_key="predictions",
                            message_type="ou_prediction",
                            fixture_id=fixture.fixture_id,
                            model_prediction_id=None,
                            dry_run=dry_run,
                            print_only=print_only,
                            payload_metadata={
                                "model_family": "ou25",
                                "ou_model_prediction_id": prediction.ou_model_prediction_id,
                                "daily_window": resolved_window.value,
                                "automation_window": resolved_window.value,
                                "automation_date": target_date.isoformat(),
                                "prediction_time": prediction_time.isoformat(),
                            },
                        )
                        discord_sent = send_result.status == "sent"
                        discord_message_id = send_result.discord_message_id
                        status = send_result.status
                    except Exception as exc:
                        logger.warning(
                            "Discord send failed for fixture %d: %s",
                            fixture.fixture_id, exc,
                        )
            elif print_only:
                md = format_ou_prediction_markdown(
                    prediction,
                    fixture,
                    timezone_name=timezone_name,
                    edge_display_threshold=edge_threshold,
                )
                print(md)
                status = "print_only"
            elif dry_run:
                status = "dry_run"

            results.append(OUDailyFixtureResult(
                fixture_id=fixture.fixture_id,
                status=status,
                kickoff=fixture.date,
                prediction_time=prediction_time,
                league_id=fixture.league_id,
                p_over=prediction.p_over,
                p_under=prediction.p_under,
                edge_over=prediction.edge_over,
                confidence_label=prediction.confidence_label,
                confidence_score=prediction.confidence_score,
                ou_model_prediction_id=prediction.ou_model_prediction_id,
                discord_message_id=discord_message_id,
                discord_sent=discord_sent,
                reason=reason,
            ))
        except Exception as exc:
            logger.error("O/U prediction failed for fixture %d: %s", fixture.fixture_id, exc)
            results.append(OUDailyFixtureResult(
                fixture_id=fixture.fixture_id,
                status="failed",
                kickoff=fixture.date,
                prediction_time=prediction_time,
                league_id=fixture.league_id,
                error=str(exc),
            ))

    return OUDailyPredictionSummary(
        target_date=target_date,
        window=resolved_window,
        results=results,
    )
