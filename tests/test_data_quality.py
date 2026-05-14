from __future__ import annotations

from datetime import UTC, datetime, timedelta

from football_predictor.features.data_quality import (
    DATA_QUALITY_VERSION,
    publication_quality_payload,
    source_quality_payload,
)

PREDICTION_TIME = datetime(2026, 5, 2, 12, tzinfo=UTC)


def test_dq_v2_source_quality_full_partial_stale_and_bounded() -> None:
    fresh = source_quality_payload(
        available=True,
        checked=True,
        count=1,
        weight=30,
        prediction_time=PREDICTION_TIME,
        latest_fetched_at=PREDICTION_TIME - timedelta(hours=2),
        fresh_minutes=6 * 60,
        partial_minutes=24 * 60,
    )
    partial = source_quality_payload(
        available=True,
        checked=True,
        count=1,
        weight=30,
        prediction_time=PREDICTION_TIME,
        latest_fetched_at=PREDICTION_TIME - timedelta(hours=8),
        fresh_minutes=6 * 60,
        partial_minutes=24 * 60,
    )
    stale = source_quality_payload(
        available=True,
        checked=True,
        count=1,
        weight=30,
        prediction_time=PREDICTION_TIME,
        latest_fetched_at=PREDICTION_TIME - timedelta(hours=30),
        fresh_minutes=6 * 60,
        partial_minutes=24 * 60,
    )

    payload = publication_quality_payload(
        {"fresh": fresh, "partial": partial, "stale": stale}
    )

    assert fresh["fresh"] is True
    assert fresh["score"] == 30
    assert partial["fresh"] is False
    assert partial["score"] == 15
    assert stale["score"] == 0
    assert payload["data_quality_version"] == DATA_QUALITY_VERSION
    assert payload["publication_data_quality_score"] == 45


def test_dq_v2_future_timestamp_adds_blocker_and_zero_score() -> None:
    source = source_quality_payload(
        available=True,
        checked=True,
        count=1,
        weight=120,
        prediction_time=PREDICTION_TIME,
        latest_fetched_at=PREDICTION_TIME + timedelta(minutes=1),
        fresh_minutes=60,
        partial_minutes=120,
    )

    payload = publication_quality_payload({"odds_1x2": source})

    assert source["score"] == 0
    assert source["available"] is False
    assert source["checked"] is False
    assert source["fresh"] is False
    assert source["count"] == 0
    assert "future_snapshot_ignored" in source["warnings"]
    assert payload["publication_data_quality_score"] == 0
    assert payload["publication_blockers"] == ["odds_1x2_future_snapshot"]
