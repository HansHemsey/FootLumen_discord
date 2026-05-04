"""Timezone and datetime helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_aware_utc(value)
    normalized = value.replace("Z", "+00:00")
    return ensure_aware_utc(datetime.fromisoformat(normalized))


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_in_timezone(value: datetime, timezone_name: str) -> str:
    return ensure_aware_utc(value).astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")
