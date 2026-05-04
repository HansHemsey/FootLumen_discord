"""API-Football specific exceptions."""

from football_predictor.utils.exceptions import (
    ApiFootballClientError,
    ApiFootballError,
    ApiFootballNoContentError,
    ApiFootballPaginationError,
    ApiFootballRateLimitError,
    ApiFootballServerError,
    ApiFootballSnapshotError,
)

__all__ = [
    "ApiFootballClientError",
    "ApiFootballError",
    "ApiFootballNoContentError",
    "ApiFootballPaginationError",
    "ApiFootballRateLimitError",
    "ApiFootballServerError",
    "ApiFootballSnapshotError",
]
