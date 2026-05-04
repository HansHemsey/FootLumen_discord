"""Point-in-time helpers used by feature builders and tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from football_predictor.utils.time import ensure_aware_utc

T = TypeVar("T")


@dataclass(frozen=True)
class TimedRecord:
    identifier: int
    available_at: datetime
    payload: object


def is_available_at(available_at: datetime, prediction_time: datetime) -> bool:
    return ensure_aware_utc(available_at) <= ensure_aware_utc(prediction_time)


def before_prediction(match_date: datetime, prediction_time: datetime) -> bool:
    return ensure_aware_utc(match_date) < ensure_aware_utc(prediction_time)


def exclude_target(records: Iterable[T], target_id: int, get_id: Callable[[T], int]) -> list[T]:
    return [record for record in records if get_id(record) != target_id]


def available_records(
    records: Iterable[TimedRecord], prediction_time: datetime
) -> list[TimedRecord]:
    return [record for record in records if is_available_at(record.available_at, prediction_time)]
