from __future__ import annotations

import logging

from football_predictor.utils.exceptions import PredictionError
from football_predictor.utils.source_health import run_observed_source, source_health_warnings


def test_run_observed_source_records_expected_failure(caplog) -> None:
    logger = logging.getLogger("football_predictor.tests.source_health.expected")

    with caplog.at_level(logging.WARNING):
        result, health = run_observed_source(
            logger=logger,
            event="test_source",
            source_name="odds",
            fixture_id=123,
            competition_key="fifa_world_cup_2026",
            operation=lambda: (_ for _ in ()).throw(PredictionError("odds unavailable")),
            warning_name="odds_failed",
        )

    assert result is None
    assert health.status == "failed"
    assert health.warning == "odds_failed"
    assert source_health_warnings([health.as_dict()]) == ["odds_failed"]
    assert "event=test_source" in caplog.text


def test_run_observed_source_sanitizes_unexpected_traceback(caplog) -> None:
    logger = logging.getLogger("football_predictor.tests.source_health.unexpected")
    marker = "".join(
        [
            "https://discord.com/api/",
            "webhooks/",
            "1234567890/",
            "abcdefghijklmnopqrstuvwxyz",
        ]
    )

    def fail() -> None:
        raise RuntimeError(f"DISCORD_WEBHOOK_URL={marker}")

    with caplog.at_level(logging.ERROR):
        result, health = run_observed_source(
            logger=logger,
            event="test_source",
            source_name="lineups",
            fixture_id=123,
            operation=fail,
            warning_name="lineups_failed",
        )

    assert result is None
    assert health.status == "failed"
    assert health.error_type == "RuntimeError"
    assert "RuntimeError" in caplog.text
    assert "traceback=" in caplog.text
    assert "<redacted>" in caplog.text
    assert marker not in caplog.text
