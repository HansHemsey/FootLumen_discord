"""Business exceptions used across the predictor."""


class FootballPredictorError(Exception):
    """Base exception for project-specific failures."""


class ApiFootballError(FootballPredictorError):
    """Generic API-Football client failure."""


class ApiFootballRateLimitError(ApiFootballError):
    """API-Football returned a rate-limit response."""


class ApiFootballNoContentError(ApiFootballError):
    """API-Football returned no content for the requested endpoint."""


class ApiFootballClientError(ApiFootballError):
    """API-Football returned a non-rate-limit 4xx response."""


class ApiFootballServerError(ApiFootballError):
    """API-Football returned a 5xx response after retries."""


class ApiFootballPaginationError(ApiFootballError):
    """API-Football pagination metadata is inconsistent."""


class ApiFootballSnapshotError(ApiFootballError):
    """Raw API-Football snapshot persistence failed."""


class ReferenceLookupError(FootballPredictorError):
    """A requested local reference entity does not exist."""


class ReferenceValidationError(ReferenceLookupError):
    """A local reference file is malformed or missing required sections."""


class DataQualityError(FootballPredictorError):
    """Feature or prediction data quality is too poor for the requested operation."""


class DiagnosticsError(FootballPredictorError):
    """Local diagnostics or observability check failed."""


class PredictionError(FootballPredictorError):
    """Prediction pipeline failure."""


class DiscordWebhookError(FootballPredictorError):
    """Discord webhook failure."""
