"""Retry policy helpers for API-Football requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Small retry policy used by the API client."""

    max_retries: int = 2

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")

    @property
    def attempts(self) -> range:
        return range(self.max_retries + 1)

    def should_retry(self, attempt_index: int, status_code: int | None = None) -> bool:
        if attempt_index >= self.max_retries:
            return False
        if status_code is None:
            return True
        return status_code >= 500
