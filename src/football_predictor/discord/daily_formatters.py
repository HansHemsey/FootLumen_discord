"""Daily Discord formatters for standings, calendar and today fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from football_predictor.discord.formatter import CODE_CLOSE, CODE_OPEN
from football_predictor.utils.time import format_in_timezone
from football_predictor.worldcup.groups import localized_group_label, worldcup_group_sort_key

DISCORD_HARD_LIMIT = 2000
DISCORD_SAFE_LIMIT = 1900


@dataclass(frozen=True)
class StandingLine:
    rank: int | None
    team_name: str
    played: int | None
    points: int | None
    goals_diff: int | None
    form: str | None = None
    group_name: str | None = None


@dataclass(frozen=True)
class FixtureLine:
    kickoff: datetime | None
    home_team: str
    away_team: str
    status: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    round_name: str | None = None
    group_name: str | None = None


def format_standings_messages(
    *,
    competition: str,
    season: int | None,
    rows: list[StandingLine],
    updated_at: datetime | None = None,
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"📊 CLASSEMENT - {competition}",
        f"Saison : {_value(season)}",
        f"Mise à jour : {_datetime_label(updated_at, timezone_name)}",
    ]
    table = [
        " #  Équipe                    MJ  Pts  Diff  Forme",
        "--  ------------------------  --  ---  ----  ------",
    ]
    lines = [_standing_row(row) for row in rows]
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Classement non disponible.",
        max_chars=max_chars,
    )


def format_worldcup_group_standings_messages(
    *,
    competition: str,
    season: int | None,
    rows: list[StandingLine],
    updated_at: datetime | None = None,
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"📊 CLASSEMENTS DE GROUPES - {competition}",
        f"Saison : {_value(season)}",
        f"Mise à jour : {_datetime_label(updated_at, timezone_name)}",
        "Format : 2 premiers + 8 meilleurs 3es qualifiés.",
    ]
    table = [
        " #  Équipe                    MJ  Pts  Diff  Forme",
        "--  ------------------------  --  ---  ----  ------",
    ]
    lines = _worldcup_group_rows(rows)
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Classements de groupes non disponibles.",
        max_chars=max_chars,
    )


def format_calendar_messages(
    *,
    competition: str,
    season: int | None,
    round_name: str | None,
    rows: list[FixtureLine],
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"🗓️ CALENDRIER - {competition}",
        f"Journée : {_value(round_name)}",
        f"Saison : {_value(season)}",
    ]
    table = [
        "Date        Heure  Match                                           Statut",
        "----------  -----  ----------------------------------------------  ------",
    ]
    lines = [_fixture_row(row, timezone_name, include_date=True) for row in rows]
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Calendrier non disponible.",
        max_chars=max_chars,
    )


def format_worldcup_group_calendar_messages(
    *,
    competition: str,
    season: int | None,
    round_name: str | None,
    rows: list[FixtureLine],
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"🗓️ CALENDRIER DE GROUPES - {competition}",
        f"Journée : {_value(round_name)}",
        f"Saison : {_value(season)}",
    ]
    table = [
        "Date        Heure  Match                                           Statut",
        "----------  -----  ----------------------------------------------  ------",
    ]
    lines = _worldcup_group_fixture_rows(rows, timezone_name)
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Calendrier de groupes non disponible.",
        max_chars=max_chars,
    )


def format_daily_matches_messages(
    *,
    competition: str,
    match_date: str,
    rows: list[FixtureLine],
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"📅 MATCHS DU JOUR - {competition}",
        f"Date : {match_date}",
    ]
    table = [
        "Heure  Match                                           Statut",
        "-----  ----------------------------------------------  ------",
    ]
    lines = [_fixture_row(row, timezone_name, include_date=False) for row in rows]
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Aucun match programmé.",
        max_chars=max_chars,
    )


def format_worldcup_daily_matches_messages(
    *,
    competition: str,
    match_date: str,
    rows: list[FixtureLine],
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> list[str]:
    header = [
        f"📅 MATCHS DU JOUR - {competition}",
        f"Date : {match_date}",
    ]
    table = [
        "Heure  Grp  Match                                           Statut",
        "-----  ---  ----------------------------------------------  ------",
    ]
    lines = [
        _worldcup_daily_fixture_row(row, timezone_name)
        for row in sorted(
            rows,
            key=lambda item: (
                item.kickoff or datetime.max,
                item.home_team,
                item.away_team,
            ),
        )
    ]
    return _split_code_messages(
        header,
        table,
        lines,
        empty_line="Aucun match programmé.",
        max_chars=max_chars,
    )


def _worldcup_group_fixture_rows(rows: list[FixtureLine], timezone_name: str) -> list[str]:
    grouped: dict[str | None, list[FixtureLine]] = {}
    for row in rows:
        grouped.setdefault(row.group_name, []).append(row)
    lines: list[str] = []
    for group_name in sorted(grouped, key=worldcup_group_sort_key):
        if lines:
            lines.append("")
        lines.append(localized_group_label(group_name))
        for row in sorted(
            grouped[group_name],
            key=lambda item: (
                item.kickoff or datetime.max,
                item.home_team,
                item.away_team,
            ),
        ):
            lines.append(_fixture_row(row, timezone_name, include_date=True))
    return lines


def _worldcup_daily_fixture_row(row: FixtureLine, timezone_name: str) -> str:
    time_part = "--:--"
    if row.kickoff is not None:
        _date_part, time_part = format_in_timezone(row.kickoff, timezone_name).split(
            " ",
            maxsplit=1,
        )
    group = _short_group_label(row.group_name)
    match = f"{row.home_team} vs {row.away_team}"
    status = _status_or_score(row)
    return f"{time_part:<5}  {group:<3}  {_clip(match, 46):<46}  {_clip(status, 6):<6}"


def _short_group_label(group_name: str | None) -> str:
    sort_index, _label = worldcup_group_sort_key(group_name)
    if 0 <= sort_index < 26:
        return chr(ord("A") + sort_index)
    return "-"


def _worldcup_group_rows(rows: list[StandingLine]) -> list[str]:
    grouped: dict[str | None, list[StandingLine]] = {}
    for row in rows:
        grouped.setdefault(row.group_name, []).append(row)
    lines: list[str] = []
    for group_name in sorted(grouped, key=worldcup_group_sort_key):
        if lines:
            lines.append("")
        lines.append(localized_group_label(group_name))
        for row in sorted(
            grouped[group_name],
            key=lambda item: (
                item.rank if item.rank is not None else 9999,
                item.team_name,
            ),
        ):
            lines.append(_standing_row(row))
    third_place_rows = _provisional_third_place_rows(rows)
    if third_place_rows:
        lines.extend(["", "Meilleurs 3es provisoires"])
        lines.extend(_standing_row(row) for row in third_place_rows)
    return lines


def _provisional_third_place_rows(rows: list[StandingLine]) -> list[StandingLine]:
    if not any((row.played or 0) > 0 for row in rows):
        return []
    third_place_rows = [row for row in rows if row.rank == 3]
    return sorted(
        third_place_rows,
        key=lambda item: (
            item.points if item.points is not None else -9999,
            item.goals_diff if item.goals_diff is not None else -9999,
            item.team_name,
        ),
        reverse=True,
    )[:8]


def _standing_row(row: StandingLine) -> str:
    return (
        f"{_int(row.rank, 2)}  "
        f"{_clip(row.team_name, 24):<24}  "
        f"{_int(row.played, 2)}  "
        f"{_int(row.points, 3)}  "
        f"{_signed(row.goals_diff, 4)}  "
        f"{_clip(row.form or '-', 6):<6}"
    )


def _split_code_messages(
    header: list[str],
    table: list[str],
    rows: list[str],
    *,
    empty_line: str,
    max_chars: int,
) -> list[str]:
    if max_chars > DISCORD_HARD_LIMIT:
        raise ValueError("max_chars must not exceed Discord's 2000 character limit")
    body_rows = rows or [empty_line]
    chunks = _chunk_rows(header, table, body_rows, max_chars=max_chars, part_label=None)
    if len(chunks) == 1:
        return [_render_message(header, table, chunks[0], part_label=None)]
    total = len(chunks)
    chunks = _chunk_rows(
        header,
        table,
        body_rows,
        max_chars=max_chars,
        part_label=f"Partie 000/{total:03d}",
    )
    total = len(chunks)
    messages = [
        _render_message(
            header,
            table,
            chunk,
            part_label=f"Partie {index}/{total}",
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
    return [_ensure_limit(message, max_chars) for message in messages]


def _chunk_rows(
    header: list[str],
    table: list[str],
    rows: list[str],
    *,
    max_chars: int,
    part_label: str | None,
) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    for row in rows:
        safe_row = _clip(row, 220)
        candidate = [*current, safe_row]
        candidate_message = _render_message(header, table, candidate, part_label=part_label)
        if current and len(candidate_message) > max_chars:
            chunks.append(current)
            current = [safe_row]
        else:
            current = candidate
        if len(_render_message(header, table, current, part_label=part_label)) > max_chars:
            current = [_fit_single_row(header, table, safe_row, max_chars, part_label)]
    if current:
        chunks.append(current)
    return chunks


def _render_message(
    header: list[str],
    table: list[str],
    rows: list[str],
    *,
    part_label: str | None,
) -> str:
    lines = [CODE_OPEN, *header]
    if part_label is not None:
        lines.append(part_label)
    lines.extend(["", *table, *rows, CODE_CLOSE])
    return "\n".join(lines)


def _fit_single_row(
    header: list[str],
    table: list[str],
    row: str,
    max_chars: int,
    part_label: str | None,
) -> str:
    overhead = len(_render_message(header, table, [""], part_label=part_label))
    available = max(1, max_chars - overhead)
    return _clip(row, available)


def _ensure_limit(message: str, max_chars: int) -> str:
    if len(message) <= max_chars:
        return message
    lines = message.splitlines()
    if len(lines) <= 2:
        return message[: max_chars - 3] + "..."
    available = max_chars - len("\n".join([*lines[:-2], "", lines[-1]]))
    lines[-2] = _clip(lines[-2], max(1, available))
    return "\n".join(lines)


def _fixture_row(row: FixtureLine, timezone_name: str, *, include_date: bool) -> str:
    date_part = "----------"
    time_part = "--:--"
    if row.kickoff is not None:
        formatted = format_in_timezone(row.kickoff, timezone_name)
        date_part, time_part = formatted.split(" ", maxsplit=1)
    match = f"{row.home_team} vs {row.away_team}"
    status = _status_or_score(row)
    if include_date:
        return f"{date_part:<10}  {time_part:<5}  {_clip(match, 46):<46}  {_clip(status, 6):<6}"
    return f"{time_part:<5}  {_clip(match, 46):<46}  {_clip(status, 6):<6}"


def _status_or_score(row: FixtureLine) -> str:
    if row.home_goals is not None and row.away_goals is not None:
        return f"{row.home_goals}-{row.away_goals}"
    return row.status or "-"


def _datetime_label(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return "non disponible"
    return f"{format_in_timezone(value, timezone_name)} {timezone_name}"


def _value(value: object) -> str:
    return str(value) if value is not None else "non disponible"


def _int(value: int | None, width: int) -> str:
    return f"{value:>{width}d}" if value is not None else "-".rjust(width)


def _signed(value: int | None, width: int) -> str:
    return f"{value:+{width}d}" if value is not None else "-".rjust(width)


def _clip(value: object, width: int) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"
