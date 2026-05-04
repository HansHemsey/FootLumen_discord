"""Scheduling helpers for daily prediction runs."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from football_predictor.utils.time import ensure_aware_utc, utc_now


class DailyPredictionWindow(StrEnum):
    """Supported prediction cutoffs for a fixture."""

    EARLY = "early"
    MID = "mid"
    LATE = "late"
    NOW = "now"
    ALL = "all"


WINDOW_OFFSETS = {
    DailyPredictionWindow.EARLY: timedelta(hours=24),
    DailyPredictionWindow.MID: timedelta(hours=6),
    DailyPredictionWindow.LATE: timedelta(minutes=30),
}


def parse_daily_window(value: DailyPredictionWindow | str) -> DailyPredictionWindow:
    """Parse a CLI/user window value."""
    return DailyPredictionWindow(str(value))


def prediction_time_for_fixture(
    kickoff: datetime,
    window: DailyPredictionWindow | str,
    *,
    now: datetime | None = None,
) -> datetime:
    """Return the point-in-time cutoff for a fixture/window.

    `early` and `mid` simulate scheduled predictions before kickoff. `late` and
    `now` use the current timestamp. `all` is accepted as a compatibility alias
    for `now` in the daily runner.
    """
    resolved = parse_daily_window(window)
    if resolved in {
        DailyPredictionWindow.NOW,
        DailyPredictionWindow.ALL,
        DailyPredictionWindow.LATE,
    }:
        return ensure_aware_utc(now or utc_now())
    return ensure_aware_utc(kickoff) - WINDOW_OFFSETS[resolved]


def fixture_matches_window(
    kickoff: datetime | None,
    window: DailyPredictionWindow | str,
    now: datetime | None = None,
) -> bool:
    """Return whether an upcoming fixture belongs to a daily prediction window."""
    if kickoff is None:
        return False
    resolved = parse_daily_window(window)
    current_time = ensure_aware_utc(now or utc_now())
    kickoff_utc = ensure_aware_utc(kickoff)
    delta = kickoff_utc - current_time
    if delta < timedelta(0):
        return False
    if resolved in {DailyPredictionWindow.NOW, DailyPredictionWindow.ALL}:
        return True
    if resolved == DailyPredictionWindow.EARLY:
        return delta > timedelta(hours=6)
    if resolved == DailyPredictionWindow.MID:
        return timedelta(hours=1) <= delta <= timedelta(hours=6)
    return timedelta(0) <= delta <= timedelta(minutes=30)


def daily_run_key(
    target_date: str,
    window: DailyPredictionWindow | str,
    league_ids: tuple[int, ...],
    season: int | None,
) -> str:
    """Build a stable run key for logs and payload metadata."""
    league_part = ",".join(str(league_id) for league_id in league_ids) or "all"
    season_part = str(season) if season is not None else "any"
    return f"{target_date}:{parse_daily_window(window).value}:{league_part}:{season_part}"
