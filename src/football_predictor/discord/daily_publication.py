"""Publish daily operational Discord messages from local DB snapshots."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from football_predictor.config.competitions import CompetitionConfig
from football_predictor.db import models
from football_predictor.discord.daily_formatters import (
    FixtureLine,
    StandingLine,
    format_calendar_messages,
    format_daily_matches_messages,
    format_standings_messages,
)
from football_predictor.discord.service import DiscordDeliveryService


@dataclass(frozen=True)
class DailyDiscordPublishResult:
    competition_key: str | None
    league_id: int
    season: int
    channel_key: str
    message_type: str
    status: str
    message_count: int
    discord_message_ids: list[int] = field(default_factory=list)
    replaced_count: int = 0
    replace_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "competition_key": self.competition_key,
            "league_id": self.league_id,
            "season": self.season,
            "channel_key": self.channel_key,
            "message_type": self.message_type,
            "status": self.status,
            "message_count": self.message_count,
            "discord_message_ids": self.discord_message_ids,
            "replaced_count": self.replaced_count,
            "replace_warnings": self.replace_warnings,
        }


@dataclass(frozen=True)
class DailyDiscordPublishSummary:
    target_date: date
    results: list[DailyDiscordPublishResult]

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

    def as_dict(self) -> dict[str, object]:
        return {
            "target_date": self.target_date.isoformat(),
            "sent": self.sent,
            "dry_run": self.dry_run,
            "print_only": self.print_only,
            "duplicate_skipped": self.duplicate_skipped,
            "results": [result.as_dict() for result in self.results],
        }


def publish_daily_discord_messages(
    *,
    session: Session,
    competitions: Sequence[CompetitionConfig],
    delivery: DiscordDeliveryService,
    target_date: date,
    timezone_name: str = "Europe/Paris",
    include_standings: bool = True,
    include_calendar: bool = True,
    include_daily_matches: bool = True,
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    replace_previous: bool = True,
    echo: Callable[[str], None] | None = None,
) -> DailyDiscordPublishSummary:
    results: list[DailyDiscordPublishResult] = []
    for competition in competitions:
        if not competition.enabled:
            continue
        if include_standings:
            messages = _standings_messages(session, competition, timezone_name)
            results.append(
                _send_messages(
                    delivery,
                    competition,
                    messages,
                    channel_key="classement",
                    message_type="standings",
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    replace_previous=replace_previous,
                    echo=echo,
                )
            )
        if include_calendar:
            messages = _calendar_messages(session, competition, target_date, timezone_name)
            results.append(
                _send_messages(
                    delivery,
                    competition,
                    messages,
                    channel_key="calendrier",
                    message_type="schedule",
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    replace_previous=replace_previous,
                    echo=echo,
                )
            )
        if include_daily_matches:
            messages = _daily_matches_messages(session, competition, target_date, timezone_name)
            results.append(
                _send_messages(
                    delivery,
                    competition,
                    messages,
                    channel_key="matchs_du_jour",
                    message_type="daily_matches",
                    dry_run=dry_run,
                    print_only=print_only,
                    force=force,
                    replace_previous=replace_previous,
                    echo=echo,
                )
            )
    return DailyDiscordPublishSummary(target_date=target_date, results=results)


def _send_messages(
    delivery: DiscordDeliveryService,
    competition: CompetitionConfig,
    messages: list[str],
    *,
    channel_key: str,
    message_type: str,
    dry_run: bool,
    print_only: bool,
    force: bool,
    replace_previous: bool,
    echo: Callable[[str], None] | None,
) -> DailyDiscordPublishResult:
    statuses: list[str] = []
    ids: list[int] = []
    replace_summary = (
        delivery.replace_previous_messages(
            league_id=competition.league_id,
            season=competition.season,
            channel_key=channel_key,
            message_type=message_type,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
        )
        if replace_previous and _is_replaceable_daily_route(channel_key, message_type)
        else {"deleted": 0, "errors": []}
    )
    for message in messages:
        if echo is not None and print_only:
            echo(message)
        result = delivery.send_markdown(
            message,
            competition_key=None,
            league_id=competition.league_id,
            season=competition.season,
            channel_key=channel_key,
            message_type=message_type,
            dry_run=dry_run,
            print_only=print_only,
            force=force,
            wait=True,
        )
        statuses.append(result.status)
        if result.discord_message_id is not None:
            ids.append(result.discord_message_id)
    return DailyDiscordPublishResult(
        competition_key=competition.key,
        league_id=competition.league_id,
        season=competition.season,
        channel_key=channel_key,
        message_type=message_type,
        status=_combined_status(statuses),
        message_count=len(messages),
        discord_message_ids=ids,
        replaced_count=_int_summary_value(replace_summary, "deleted"),
        replace_warnings=_replace_warnings(replace_summary),
    )


def _combined_status(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    if all(status == statuses[0] for status in statuses):
        return statuses[0]
    if "sent" in statuses:
        return "sent"
    if "dry_run" in statuses:
        return "dry_run"
    if "print_only" in statuses:
        return "print_only"
    return statuses[0]


def _is_replaceable_daily_route(channel_key: str, message_type: str) -> bool:
    return (channel_key, message_type) in {
        ("classement", "standings"),
        ("calendrier", "schedule"),
        ("matchs_du_jour", "daily_matches"),
    }


def _replace_warnings(summary: dict[str, object]) -> list[str]:
    raw_errors = summary.get("errors", [])
    errors = raw_errors if isinstance(raw_errors, list) else []
    warnings = [str(item) for item in errors if str(item)]
    missing = _int_summary_value(summary, "missing_message_ids")
    if missing:
        warnings.append(f"missing_discord_message_ids={missing}")
    return warnings


def _int_summary_value(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0


def _standings_messages(
    session: Session,
    competition: CompetitionConfig,
    timezone_name: str,
) -> list[str]:
    latest = session.execute(
        select(func.max(models.StandingSnapshot.snapshot_date)).where(
            models.StandingSnapshot.league_id == competition.league_id,
            models.StandingSnapshot.season == competition.season,
        )
    ).scalar_one_or_none()
    rows: list[StandingLine] = []
    if latest is not None:
        records = session.execute(
            select(models.StandingSnapshot, models.Team.name)
            .join(models.Team, models.Team.team_id == models.StandingSnapshot.team_id, isouter=True)
            .where(
                models.StandingSnapshot.league_id == competition.league_id,
                models.StandingSnapshot.season == competition.season,
                models.StandingSnapshot.snapshot_date == latest,
            )
        ).all()
        for snapshot, team_name in sorted(
            records,
            key=lambda item: item[0].rank if item[0].rank is not None else 9999,
        ):
            rows.append(
                StandingLine(
                    rank=snapshot.rank,
                    team_name=team_name or f"Team {snapshot.team_id}",
                    played=snapshot.played or snapshot.all_played,
                    points=snapshot.points,
                    goals_diff=snapshot.goals_diff,
                    form=snapshot.form,
                )
            )
    return format_standings_messages(
        competition=competition.name,
        season=competition.season,
        rows=rows,
        updated_at=latest,
        timezone_name=timezone_name,
    )


def _calendar_messages(
    session: Session,
    competition: CompetitionConfig,
    target_date: date,
    timezone_name: str,
) -> list[str]:
    start_utc, _ = _date_bounds(target_date, timezone_name)
    first_fixture = session.execute(
        select(models.Fixture)
        .where(
            models.Fixture.league_id == competition.league_id,
            models.Fixture.season == competition.season,
            models.Fixture.date.is_not(None),
            models.Fixture.date >= start_utc,
        )
        .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        .limit(1)
    ).scalar_one_or_none()
    round_name = first_fixture.round if first_fixture is not None else None
    rows: list[FixtureLine] = []
    if round_name:
        fixtures = session.execute(
            select(models.Fixture)
            .where(
                models.Fixture.league_id == competition.league_id,
                models.Fixture.season == competition.season,
                models.Fixture.round == round_name,
            )
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        ).scalars()
        rows = [_fixture_line(fixture) for fixture in fixtures]
    return format_calendar_messages(
        competition=competition.name,
        season=competition.season,
        round_name=round_name,
        rows=rows,
        timezone_name=timezone_name,
    )


def _daily_matches_messages(
    session: Session,
    competition: CompetitionConfig,
    target_date: date,
    timezone_name: str,
) -> list[str]:
    start_utc, end_utc = _date_bounds(target_date, timezone_name)
    fixtures = session.execute(
        select(models.Fixture)
        .where(
            models.Fixture.league_id == competition.league_id,
            models.Fixture.season == competition.season,
            models.Fixture.date.is_not(None),
            models.Fixture.date >= start_utc,
            models.Fixture.date < end_utc,
        )
        .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
    ).scalars()
    return format_daily_matches_messages(
        competition=competition.name,
        match_date=target_date.isoformat(),
        rows=[_fixture_line(fixture) for fixture in fixtures],
        timezone_name=timezone_name,
    )


def _fixture_line(fixture: models.Fixture) -> FixtureLine:
    return FixtureLine(
        kickoff=fixture.date,
        home_team=fixture.home_team,
        away_team=fixture.away_team,
        status=fixture.status_short or fixture.status,
        home_goals=fixture.home_goals if fixture.home_goals is not None else fixture.goals_home,
        away_goals=fixture.away_goals if fixture.away_goals is not None else fixture.goals_away,
        round_name=fixture.round,
    )


def _date_bounds(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    start_local = datetime.combine(target_date, time.min, tzinfo=timezone)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
