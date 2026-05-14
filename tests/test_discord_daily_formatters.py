from __future__ import annotations

from datetime import UTC, datetime

from football_predictor.discord.daily_formatters import (
    FixtureLine,
    StandingLine,
    format_calendar_messages,
    format_daily_matches_messages,
    format_standings_messages,
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


def test_daily_matches_formatter_handles_no_matches() -> None:
    messages = format_daily_matches_messages(
        competition="Synthetic Daily League",
        match_date="2026-05-02",
        rows=[],
    )

    assert len(messages) == 1
    assert "Aucun match programmé" in messages[0]
    assert len(messages[0]) <= 1900


def test_daily_formatters_mask_secret_like_text() -> None:
    webhook = "https://discord.com/api/webhooks/123456/synthetic-secret"
    api_key = "synthetic-api-key-value"

    messages = format_daily_matches_messages(
        competition=f"League {webhook}",
        match_date="2026-05-02",
        rows=[
            FixtureLine(
                datetime(2026, 5, 2, 18, 0, tzinfo=UTC),
                f"Home api_key={api_key}",
                "Away",
                "NS",
            )
        ],
    )

    rendered = "\n".join(messages)
    assert webhook not in rendered
    assert api_key not in rendered
    assert "[secret masqué]" in rendered
