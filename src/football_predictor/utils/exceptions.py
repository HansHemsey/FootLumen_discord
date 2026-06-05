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


class DataSourceUnavailable(FootballPredictorError):
    """A dynamic source failed or returned unusable data."""


class OddsUnavailable(DataSourceUnavailable):
    """Prematch odds are unavailable or failed to refresh."""


class LineupsUnavailable(DataSourceUnavailable):
    """Lineups are unavailable or failed to refresh."""


class ApiPredictionUnavailable(DataSourceUnavailable):
    """API-Football prediction snapshot is unavailable or failed to refresh."""


class StaleSnapshotError(DataSourceUnavailable):
    """A point-in-time snapshot is too old for the requested use."""


class PublicationBlocked(FootballPredictorError):
    """Publication was blocked by a safety or data-quality policy."""


class DataLeakageGuardError(FootballPredictorError):
    """A point-in-time guard detected future data usage."""


class DiagnosticsError(FootballPredictorError):
    """Local diagnostics or observability check failed."""


class PredictionError(FootballPredictorError):
    """Prediction pipeline failure."""


class DiscordWebhookError(FootballPredictorError):
    """Discord webhook failure."""
