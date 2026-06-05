"""Read-only session builder for World Cup combo candidates."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db.models import Fixture
from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.models import (
    WorldCupComboFixtureRef,
    WorldCupComboSession,
)

GROUP_STAGE = "GROUP"
KNOCKOUT_STAGE = "KNOCKOUT"
UNKNOWN_STAGE = "UNKNOWN"
MIXED_STAGE = "MIXED"


class WorldCupComboSessionService:
    """Build hourly fixture sessions without mutating predictions or DB state."""

    def __init__(self, db_session: Session, config: WorldCupComboConfig) -> None:
        self.db_session = db_session
        self.config = config
        self.display_timezone = ZoneInfo(config.timezone_display)

    def build_sessions(self, target_date: date | None = None) -> list[WorldCupComboSession]:
        if not self.config.enabled:
            return []

        fixtures = self._load_fixture_refs()
        if target_date is not None:
            fixtures = [
                fixture
                for fixture in fixtures
                if fixture.kickoff_at_paris.date() == target_date
            ]

        fixtures_by_date: dict[date, list[WorldCupComboFixtureRef]] = defaultdict(list)
        for fixture in fixtures:
            fixtures_by_date[fixture.kickoff_at_paris.date()].append(fixture)

        sessions: list[WorldCupComboSession] = []
        max_span = timedelta(hours=max(self.config.max_session_span_hours_public, 1))
        for combo_date in sorted(fixtures_by_date):
            day_fixtures = sorted(
                fixtures_by_date[combo_date],
                key=lambda item: item.kickoff_at_utc,
            )
            grouped: list[list[WorldCupComboFixtureRef]] = []
            current: list[WorldCupComboFixtureRef] = []
            session_start: datetime | None = None
            for fixture in day_fixtures:
                if session_start is None or not current:
                    current = [fixture]
                    session_start = fixture.kickoff_at_utc
                    continue
                if fixture.kickoff_at_utc - session_start > max_span:
                    grouped.append(current)
                    current = [fixture]
                    session_start = fixture.kickoff_at_utc
                else:
                    current.append(fixture)
            if current:
                grouped.append(current)

            for index, group in enumerate(grouped, start=1):
                sessions.append(self._session_from_group(combo_date, index, tuple(group)))
        return sessions

    def _load_fixture_refs(self) -> list[WorldCupComboFixtureRef]:
        statement = (
            select(Fixture)
            .where(Fixture.league_id == self.config.league_id)
            .where(Fixture.season == self.config.season)
            .where(Fixture.date.is_not(None))
            .order_by(Fixture.date.asc(), Fixture.fixture_id.asc())
        )
        refs: list[WorldCupComboFixtureRef] = []
        for fixture in self.db_session.execute(statement).scalars():
            kickoff_utc = _as_utc(fixture.date)
            kickoff_paris = kickoff_utc.astimezone(self.display_timezone)
            stage, group_matchday, stage_warnings = detect_fixture_stage(fixture.round)
            refs.append(
                WorldCupComboFixtureRef(
                    fixture_id=fixture.fixture_id,
                    kickoff_at_utc=kickoff_utc,
                    kickoff_at_paris=kickoff_paris,
                    home_team=fixture.home_team,
                    away_team=fixture.away_team,
                    status_short=fixture.status_short,
                    round_name=fixture.round,
                    league_id=fixture.league_id,
                    season=fixture.season,
                    competition_key=self.config.competition_key,
                    warnings=stage_warnings,
                )
            )
        return refs

    def _session_from_group(
        self,
        combo_date: date,
        index: int,
        fixtures: tuple[WorldCupComboFixtureRef, ...],
    ) -> WorldCupComboSession:
        first_kickoff = min(fixture.kickoff_at_utc for fixture in fixtures)
        last_kickoff = max(fixture.kickoff_at_utc for fixture in fixtures)
        session_key = _session_key(combo_date, index, fixtures)
        stages: list[str] = []
        matchdays: list[int] = []
        warnings: list[str] = []
        for fixture in fixtures:
            stage, group_matchday, stage_warnings = detect_fixture_stage(fixture.round_name)
            stages.append(stage)
            if group_matchday is not None:
                matchdays.append(group_matchday)
            warnings.extend(stage_warnings)

        stage = _session_stage(stages)
        group_matchday = matchdays[0] if matchdays and len(set(matchdays)) == 1 else None
        if len(set(matchdays)) > 1:
            warnings.append("mixed_group_matchdays")
        return WorldCupComboSession(
            session_key=session_key,
            combo_date_paris=combo_date,
            first_kickoff_at=first_kickoff,
            last_kickoff_at=last_kickoff,
            fixtures=fixtures,
            stage=stage,
            group_matchday=group_matchday,
            is_matchday3=group_matchday == 3,
            is_knockout=stage == KNOCKOUT_STAGE,
            lock_time=first_kickoff - timedelta(minutes=self.config.lock_buffer_minutes),
            warnings=_dedupe(warnings),
        )


def detect_fixture_stage(round_name: str | None) -> tuple[str, int | None, list[str]]:
    if not round_name:
        return UNKNOWN_STAGE, None, ["match_scope_ambiguous"]

    normalized = round_name.strip().lower()
    if any(
        token in normalized
        for token in (
            "round of 16",
            "quarter",
            "semi",
            "third place",
            "3rd place",
            "final",
            "knockout",
        )
    ):
        return KNOCKOUT_STAGE, None, []

    if "group" in normalized:
        matchday = _parse_group_matchday(normalized)
        warnings = [] if matchday is not None else ["group_matchday_ambiguous"]
        return GROUP_STAGE, matchday, warnings

    return UNKNOWN_STAGE, None, ["match_scope_ambiguous"]


def _parse_group_matchday(round_name: str) -> int | None:
    patterns = (
        r"matchday\s*(\d+)",
        r"round\s*(\d+)",
        r"(?:^|\D)([123])(?:\D|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, round_name)
        if match:
            value = int(match.group(1))
            if value in {1, 2, 3}:
                return value
    return None


def _session_stage(stages: list[str]) -> str:
    non_unknown = [stage for stage in stages if stage != UNKNOWN_STAGE]
    if not non_unknown:
        return UNKNOWN_STAGE
    unique = set(non_unknown)
    if len(unique) == 1:
        return non_unknown[0]
    return MIXED_STAGE


def _session_key(
    combo_date: date,
    index: int,
    fixtures: tuple[WorldCupComboFixtureRef, ...],
) -> str:
    fixture_part = "-".join(str(fixture.fixture_id) for fixture in fixtures)
    return f"wc-combos:{combo_date.isoformat()}:{index}:{fixture_part}"


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("fixture kickoff date is required")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
