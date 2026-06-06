from __future__ import annotations

from datetime import UTC, datetime

from football_predictor.discord.daily_formatters import (
    FixtureLine,
    StandingLine,
    format_calendar_messages,
    format_daily_matches_messages,
    format_standings_messages,
    format_worldcup_daily_matches_messages,
    format_worldcup_group_calendar_messages,
    format_worldcup_group_standings_messages,
)


def test_standings_formatter_single_message() -> None:
    messages = format_standings_messages(
        competition="Synthetic League",
        season=2026,
        rows=[
            StandingLine(1, "Synthetic Team A", 10, 24, 12, "WWD"),
            StandingLine(2, "Synthetic Team B", 10, 21, 8, "WLW"),
        ],
        updated_at=datetime(2026, 5, 2, 10, 0, tzinfo=UTC),
    )

    assert len(messages) == 1
    assert messages[0].startswith("```md")
    assert messages[0].endswith("```")
    assert "CLASSEMENT" in messages[0]
    assert "Synthetic Team A" in messages[0]
    assert len(messages[0]) <= 1900


def test_standings_formatter_splits_long_table_under_discord_limit() -> None:
    rows = [
        StandingLine(
            index,
            f"Synthetic Very Long Team Name {index}",
            38,
            80 - index,
            index,
            "WWWWW",
        )
        for index in range(1, 80)
    ]

    messages = format_standings_messages(
        competition="Synthetic Long League",
        season=2026,
        rows=rows,
        max_chars=800,
    )

    assert len(messages) > 1
    assert all(message.startswith("```md") and message.endswith("```") for message in messages)
    assert all(len(message) <= 800 for message in messages)
    assert "Partie 1/" in messages[0]


def test_worldcup_group_standings_formatter_groups_rows_and_handles_unknown() -> None:
    messages = format_worldcup_group_standings_messages(
        competition="FIFA World Cup",
        season=2026,
        rows=[
            StandingLine(2, "South Africa", 0, 0, 0, None, "Group A"),
            StandingLine(1, "Mexico", 0, 0, 0, None, "Group A"),
            StandingLine(1, "England", 0, 0, 0, None, "Group L"),
            StandingLine(1, "Synthetic Unknown", 0, 0, 0, None, None),
        ],
        updated_at=datetime(2026, 5, 26, 0, 0, tzinfo=UTC),
    )

    message = messages[0]

    assert len(messages) == 1
    assert "CLASSEMENTS DE GROUPES - FIFA World Cup" in message
    assert "Format : 2 premiers + 8 meilleurs 3es qualifiés." in message
    assert "Groupe A" in message
    assert "Groupe L" in message
    assert "Groupe non identifié" in message
    assert message.index("Mexico") < message.index("South Africa")
    assert message.startswith("```md") and message.endswith("```")


def test_worldcup_group_standings_formatter_adds_best_thirds_after_played_matches() -> None:
    messages = format_worldcup_group_standings_messages(
        competition="FIFA World Cup",
        season=2026,
        rows=[
            StandingLine(3, "Third A", 2, 3, 1, "WL", "Group A"),
            StandingLine(3, "Third B", 2, 4, 0, "DW", "Group B"),
            StandingLine(1, "Leader A", 2, 6, 3, "WW", "Group A"),
        ],
    )

    assert "Meilleurs 3es provisoires" in messages[0]
    best_thirds = messages[0].split("Meilleurs 3es provisoires", maxsplit=1)[1]
    assert "Third B" in best_thirds


def test_calendar_formatter_formats_next_round_and_splits() -> None:
    rows = [
        FixtureLine(
            datetime(2026, 5, 2, 18, index % 60, tzinfo=UTC),
            f"Synthetic Home {index}",
            f"Synthetic Away {index}",
            "NS",
            round_name="Regular Season - 12",
        )
        for index in range(35)
    ]

    messages = format_calendar_messages(
        competition="Synthetic Calendar League",
        season=2026,
        round_name="Regular Season - 12",
        rows=rows,
        max_chars=900,
    )

    assert len(messages) > 1
    assert all(len(message) <= 900 for message in messages)
    assert "CALENDRIER" in messages[0]
    assert "Regular Season - 12" in messages[0]


def test_worldcup_group_calendar_formatter_groups_fixtures_and_handles_unknown() -> None:
    messages = format_worldcup_group_calendar_messages(
        competition="FIFA World Cup",
        season=2026,
        round_name="Group Stage - 1",
        rows=[
            FixtureLine(
                datetime(2026, 6, 11, 19, 0, tzinfo=UTC),
                "Mexico",
                "South Africa",
                "NS",
                group_name="Group A",
            ),
            FixtureLine(
                datetime(2026, 6, 17, 20, 0, tzinfo=UTC),
                "England",
                "Croatia",
                "NS",
                group_name="Group L",
            ),
            FixtureLine(
                datetime(2026, 6, 18, 20, 0, tzinfo=UTC),
                "Unknown A",
                "Unknown B",
                "NS",
            ),
        ],
    )

    message = messages[0]

    assert len(messages) == 1
    assert "CALENDRIER DE GROUPES - FIFA World Cup" in message
    assert "Journée : Group Stage - 1" in message
    assert "Groupe A" in message
    assert "Groupe L" in message
    assert "Groupe non identifié" in message
    assert "Mexico vs South Africa" in message
    assert message.startswith("```md") and message.endswith("```")


def test_worldcup_group_calendar_formatter_splits_under_discord_limit() -> None:
    rows = [
        FixtureLine(
            datetime(2026, 6, 11, 19, index % 60, tzinfo=UTC),
            f"Synthetic Home {index}",
            f"Synthetic Away {index}",
            "NS",
            group_name=f"Group {chr(ord('A') + index % 12)}",
        )
        for index in range(60)
    ]

    messages = format_worldcup_group_calendar_messages(
        competition="FIFA World Cup",
        season=2026,
        round_name="Group Stage - 1",
        rows=rows,
        max_chars=900,
    )

    assert len(messages) > 1
    assert all(message.startswith("```md") and message.endswith("```") for message in messages)
    assert all(len(message) <= 900 for message in messages)
    assert "Partie 1/" in messages[0]


def test_daily_matches_formatter_handles_no_matches() -> None:
    messages = format_daily_matches_messages(
        competition="Synthetic Daily League",
        match_date="2026-05-02",
        rows=[],
    )

    assert len(messages) == 1
    assert "Aucun match programmé" in messages[0]
    assert len(messages[0]) <= 1900


def test_worldcup_daily_matches_formatter_adds_group_column() -> None:
    messages = format_worldcup_daily_matches_messages(
        competition="FIFA World Cup",
        match_date="2026-06-14",
        rows=[
            FixtureLine(
                datetime(2026, 6, 17, 20, 0, tzinfo=UTC),
                "England",
                "Croatia",
                "NS",
                group_name="Group L",
            ),
            FixtureLine(
                datetime(2026, 6, 14, 22, 0, tzinfo=UTC),
                "Brazil",
                "Morocco",
                "NS",
                group_name="Group C",
            ),
            FixtureLine(
                datetime(2026, 6, 18, 20, 0, tzinfo=UTC),
                "Unknown A",
                "Unknown B",
                "NS",
            ),
        ],
    )

    message = messages[0]

    assert len(messages) == 1
    assert "MATCHS DU JOUR - FIFA World Cup" in message
    assert "Heure  Grp  Match" in message
    assert "C    Brazil vs Morocco" in message
    assert "L    England vs Croatia" in message
    assert "-    Unknown A vs Unknown B" in message
    assert message.index("Brazil vs Morocco") < message.index("England vs Croatia")
    assert message.startswith("```md") and message.endswith("```")
