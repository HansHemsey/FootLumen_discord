"""Structured health records for optional job data sources."""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, TypeVar

from football_predictor.security.sanitize import sanitize_text, sanitize_value
from football_predictor.utils.exceptions import FootballPredictorError
from football_predictor.utils.logging import log_event
from football_predictor.utils.time import ensure_aware_utc, utc_now

JsonDict = dict[str, Any]
T = TypeVar("T")


@dataclass(frozen=True)
class SourceHealth:
    source_name: str
    status: str
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    error_type: str | None = None
    warning: str | None = None
    fixture_id: int | None = None
    duration_ms: float | None = None

    def as_dict(self) -> JsonDict:
        payload = asdict(self)
        payload["last_success_at"] = (
            self.last_success_at.isoformat() if self.last_success_at else None
        )
        payload["last_failure_at"] = (
            self.last_failure_at.isoformat() if self.last_failure_at else None
        )
        return sanitize_value(payload)


def run_observed_source(
    *,
    logger: logging.Logger,
    event: str,
    source_name: str,
    fixture_id: int | None,
    operation: Callable[[], T],
    warning_name: str | None = None,
    competition_key: str | None = None,
    expected_exceptions: tuple[type[BaseException], ...] = (FootballPredictorError,),
) -> tuple[T | None, SourceHealth]:
    """Run an optional data source and return sanitized health metadata.

    Expected domain failures are logged without traceback. Unexpected failures are logged
    with traceback but still converted into a failed source record so optional sources do
    not take down the whole job.
    """
    started = time.perf_counter()
    try:
        result = operation()
    except expected_exceptions as exc:
        duration_ms = _duration_ms(started)
        warning = warning_name or f"{source_name}_failed"
        health = SourceHealth(
            source_name=source_name,
            status="failed",
            last_failure_at=utc_now(),
            error_type=type(exc).__name__,
            warning=warning,
            fixture_id=fixture_id,
            duration_ms=duration_ms,
        )
        log_event(
            logger,
            "WARNING",
            event,
            fixture_id=fixture_id,
            competition_key=competition_key,
            source=source_name,
            status="failed",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            warning=warning,
            error=sanitize_text(str(exc)),
        )
        return None, health
    except Exception as exc:
        duration_ms = _duration_ms(started)
        warning = warning_name or f"{source_name}_unexpected_failure"
        health = SourceHealth(
            source_name=source_name,
            status="failed",
            last_failure_at=utc_now(),
            error_type=type(exc).__name__,
            warning=warning,
            fixture_id=fixture_id,
            duration_ms=duration_ms,
        )
        traceback_text = sanitize_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        )
        logger.error(
            "Unexpected optional source failure event=%s fixture_id=%s source=%s "
            "duration_ms=%.1f error_type=%s error=%s traceback=%r",
            sanitize_text(event),
            fixture_id,
            sanitize_text(source_name),
            duration_ms,
            type(exc).__name__,
            sanitize_text(str(exc)),
            traceback_text,
        )
        return None, health

    duration_ms = _duration_ms(started)
    health = SourceHealth(
        source_name=source_name,
        status="success",
        last_success_at=ensure_aware_utc(utc_now()),
        fixture_id=fixture_id,
        duration_ms=duration_ms,
    )
    log_event(
        logger,
        "INFO",
        event,
        fixture_id=fixture_id,
        competition_key=competition_key,
        source=source_name,
        status="success",
        duration_ms=duration_ms,
    )
    return result, health


def source_health_warnings(source_health: list[JsonDict] | tuple[JsonDict, ...]) -> list[str]:
    warnings: list[str] = []
    for row in source_health:
        if not isinstance(row, dict) or row.get("status") == "success":
            continue
        warning = row.get("warning")
        source = row.get("source_name")
        if warning:
            warnings.append(str(warning))
        elif source:
            warnings.append(f"{source}_failed")
    return sorted(set(warnings))


def _duration_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 1)
