from __future__ import annotations

from datetime import UTC, datetime, timedelta

from football_predictor.features.point_in_time import TimedRecord, available_records, exclude_target


def test_available_records_excludes_future_snapshots() -> None:
    prediction_time = datetime(2026, 5, 2, 12, tzinfo=UTC)
    records = [
        TimedRecord(identifier=1, available_at=prediction_time - timedelta(minutes=1), payload={}),
        TimedRecord(identifier=2, available_at=prediction_time + timedelta(minutes=1), payload={}),
    ]

    available = available_records(records, prediction_time)

    assert [record.identifier for record in available] == [1]


def test_exclude_target_removes_fixture_itself() -> None:
    records = [{"fixture_id": 1}, {"fixture_id": 2}]

    filtered = exclude_target(records, target_id=2, get_id=lambda row: row["fixture_id"])

    assert filtered == [{"fixture_id": 1}]
