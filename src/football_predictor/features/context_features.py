"""Calendar context features for fixture prediction."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from football_predictor.utils.time import ensure_aware_utc


def rest_days(matches: Sequence[Any], prediction_time: datetime) -> float | None:
    """Days since the latest known historical fixture before prediction_time."""
    latest = _latest_match_date(matches)
    if latest is None:
        return None
    delta = ensure_aware_utc(prediction_time) - latest
    return max(delta.total_seconds() / 86400, 0.0)


def matches_in_last_days(
    matches: Sequence[Any],
    prediction_time: datetime,
    days: int,
) -> int:
    cutoff = ensure_aware_utc(prediction_time)
    return sum(
        1
        for match in matches
        if (match_date := _match_date(match)) is not None
        and 0 <= (cutoff - match_date).total_seconds() <= days * 86400
    )


def extract_round_number(round_value: str | None) -> int | None:
    """Extract the last integer from an API-Football round label."""
    if not round_value:
        return None
    matches = re.findall(r"\d+", round_value)
    if not matches:
        return None
    return int(matches[-1])


def _latest_match_date(matches: Sequence[Any]) -> datetime | None:
    dates = [match_date for match in matches if (match_date := _match_date(match)) is not None]
    return max(dates) if dates else None


def _match_date(match: Any) -> datetime | None:
    value = getattr(match.fixture, "date", None)
    if not isinstance(value, datetime):
        return None
    return ensure_aware_utc(value)
