"""Point-in-time cutoff helpers for World Cup combo reads."""

from __future__ import annotations

from datetime import UTC, datetime


def compute_effective_cutoff(now: datetime, lock_time: datetime) -> datetime:
    """Return the latest timestamp that can be used for dynamic snapshot reads.

    ``lock_time`` is the planned ticket lock time. It can be in the future when a
    dry-run or generation job executes early in the day, so snapshot reads must
    never use it directly without comparing it to ``now``.
    """

    now_utc = _as_utc(now)
    lock_utc = _as_utc(lock_time)
    return now_utc if now_utc <= lock_utc else lock_utc


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
