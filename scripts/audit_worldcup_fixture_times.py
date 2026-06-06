#!/usr/bin/env python3
"""Audit World Cup fixture kickoff times in a display timezone.

This script is read-only. It can use the local API-Football reference JSON or
the configured database, then prints the kickoff distribution in Europe/Paris
by default.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class FixtureTimeRow:
    fixture_id: int
    kickoff_utc: datetime
    home_team: str
    away_team: str
    round_name: str | None


def main() -> None:
    args = _parse_args()
    rows = (
        _load_db_rows(args.league_id, args.season)
        if args.source == "db"
        else _load_reference_rows(args.reference, args.league_id, args.season)
    )
    if not rows:
        raise SystemExit("No World Cup fixtures found for requested source/league/season.")

    timezone = ZoneInfo(args.timezone)
    payload = _build_report(rows, timezone=timezone, night_before_hour=args.night_before_hour)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return
    _print_report(payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("reference", "db"), default="reference")
    parser.add_argument("--reference", type=Path, default=Path("docs/api_football_reference.json"))
    parser.add_argument("--league-id", type=int, default=1)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--timezone", default="Europe/Paris")
    parser.add_argument("--night-before-hour", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _load_reference_rows(path: Path, league_id: int, season: int) -> list[FixtureTimeRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for competition in payload.get("competitions", []):
        target = competition.get("target") if isinstance(competition, dict) else {}
        league = competition.get("league") if isinstance(competition, dict) else {}
        target_key = target.get("key") if isinstance(target, dict) else None
        if target_key != "fifa_world_cup_2026" and not (
            isinstance(league, dict)
            and league.get("id") == league_id
            and league.get("season") == season
        ):
            continue
        return [
            FixtureTimeRow(
                fixture_id=int(fixture["fixture_id"]),
                kickoff_utc=_parse_datetime(str(fixture["date"])),
                home_team=str(fixture["home_team"]),
                away_team=str(fixture["away_team"]),
                round_name=fixture.get("round"),
            )
            for fixture in competition.get("fixtures", [])
            if fixture.get("fixture_id")
            and fixture.get("date")
            and fixture.get("home_team")
            and fixture.get("away_team")
        ]
    return []


def _load_db_rows(league_id: int, season: int) -> list[FixtureTimeRow]:
    from sqlalchemy import select

    from football_predictor.config.settings import get_settings
    from football_predictor.db import models
    from football_predictor.db.session import (
        create_db_engine,
        create_session_factory,
        session_scope,
    )

    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        fixtures = session.execute(
            select(models.Fixture)
            .where(models.Fixture.league_id == league_id)
            .where(models.Fixture.season == season)
            .where(models.Fixture.date.is_not(None))
            .order_by(models.Fixture.date.asc(), models.Fixture.fixture_id.asc())
        ).scalars()
        return [
            FixtureTimeRow(
                fixture_id=fixture.fixture_id,
                kickoff_utc=_parse_datetime(fixture.date.isoformat()),
                home_team=fixture.home_team,
                away_team=fixture.away_team,
                round_name=fixture.round,
            )
            for fixture in fixtures
            if fixture.date is not None
        ]


def _build_report(
    rows: list[FixtureTimeRow],
    *,
    timezone: ZoneInfo,
    night_before_hour: int,
) -> dict[str, object]:
    converted = [
        (row.kickoff_utc.astimezone(timezone), row)
        for row in sorted(rows, key=lambda item: (item.kickoff_utc, item.fixture_id))
    ]
    hour_counts = Counter(local.hour for local, _row in converted)
    time_counts = Counter(local.strftime("%H:%M") for local, _row in converted)
    by_day: dict[str, list[str]] = defaultdict(list)
    night_rows: list[dict[str, object]] = []
    for local, row in converted:
        label = f"{local.strftime('%H:%M')} {row.home_team} vs {row.away_team}"
        by_day[local.date().isoformat()].append(label)
        if local.hour < night_before_hour:
            night_rows.append(_row_payload(local, row))

    return {
        "timezone": timezone.key,
        "fixture_count": len(converted),
        "date_range": {
            "first": converted[0][0].strftime("%Y-%m-%d %H:%M"),
            "last": converted[-1][0].strftime("%Y-%m-%d %H:%M"),
        },
        "unique_times": sorted(time_counts),
        "time_counts": dict(sorted(time_counts.items())),
        "hour_counts": {f"{hour:02d}:00": count for hour, count in sorted(hour_counts.items())},
        "night_before_hour": night_before_hour,
        "night_fixture_count": len(night_rows),
        "night_fixtures": night_rows,
        "by_local_day": {day: values for day, values in sorted(by_day.items())},
    }


def _row_payload(local: datetime, row: FixtureTimeRow) -> dict[str, object]:
    return {
        "fixture_id": row.fixture_id,
        "kickoff_local": local.strftime("%Y-%m-%d %H:%M"),
        "round": row.round_name,
        "home_team": row.home_team,
        "away_team": row.away_team,
    }


def _print_report(payload: dict[str, object]) -> None:
    print(f"Timezone: {payload['timezone']}")
    print(f"Fixtures: {payload['fixture_count']}")
    date_range = payload["date_range"]
    if isinstance(date_range, dict):
        print(f"Date range: {date_range['first']} -> {date_range['last']}")
    print(f"Unique times: {', '.join(payload['unique_times'])}")
    print("Hour counts:")
    for hour, count in payload["hour_counts"].items():
        print(f"  {hour}: {count}")
    print(
        f"Night fixtures before {int(payload['night_before_hour']):02d}:00: "
        f"{payload['night_fixture_count']}"
    )
    for row in payload["night_fixtures"]:
        print(
            f"  {row['kickoff_local']} | {row['round']} | "
            f"{row['home_team']} vs {row['away_team']}"
        )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("UTC"))


if __name__ == "__main__":
    main()
