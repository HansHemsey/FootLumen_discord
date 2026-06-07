"""Common public DTOs and sanitizers for the FootLumen API."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from football_predictor.security.sanitize import contains_sensitive_data, sanitize_text

PARIS_TZ = ZoneInfo("Europe/Paris")

_PUBLIC_WARNING_MAP: dict[str, tuple[str, str, str]] = {
    "odds_missing": ("odds_missing", "Cotes indisponibles", "medium"),
    "odds_stale": ("odds_stale", "Cotes a rafraichir", "medium"),
    "lineup_missing_close_to_kickoff": (
        "lineup_missing",
        "Composition non confirmee",
        "medium",
    ),
    "lineup_missing": ("lineup_missing", "Composition non confirmee", "medium"),
    "lineup_risk_too_high": ("lineup_risk", "Risque composition eleve", "high"),
    "data_quality_below_threshold": (
        "data_quality_low",
        "Qualite des donnees insuffisante",
        "high",
    ),
    "data_quality_insufficient": (
        "data_quality_low",
        "Qualite des donnees insuffisante",
        "high",
    ),
    "draw_probability_underestimated": (
        "draw_risk",
        "Risque de nul eleve",
        "medium",
    ),
    "worldcup_balanced_match_draw_cap": (
        "draw_risk",
        "Match equilibre, confiance plafonnee",
        "medium",
    ),
    "fixture_not_ns": ("fixture_status", "Match non eligible", "high"),
    "market_scope_unknown": ("market_scope", "Marche a verifier", "high"),
    "no_clean_replacement": ("combo_no_replacement", "Aucun remplacement propre", "high"),
    "replacement_used": ("combo_replacement", "Selection remplacee avant verrouillage", "low"),
}


class PublicModel(BaseModel):
    """Base class for public API DTOs."""

    model_config = ConfigDict(extra="forbid")


class ApiMeta(PublicModel):
    api_version: str = "v1"
    generated_at: datetime


class ApiError(PublicModel):
    code: str
    message: str


class PaginationMeta(PublicModel):
    limit: int
    offset: int = 0
    total: int | None = None
    has_more: bool = False


class CompetitionSummary(PublicModel):
    competition_key: str | None = None
    league_id: int | None = None
    season: int | None = None
    name: str | None = None
    country: str | None = None
    type: str | None = None
    enabled: bool | None = None
    logo: str | None = None
    category: str | None = None


class TeamSummary(PublicModel):
    team_id: int | None = None
    name: str | None = None
    code: str | None = None
    country: str | None = None


class PublicWarning(PublicModel):
    code: str
    message: str
    severity: str = "medium"


class DataQualitySummary(PublicModel):
    score: float | None = None
    label: str | None = None
    warnings: list[PublicWarning] = []


class ConfidenceSummary(PublicModel):
    score: float | None = None
    label: str | None = None


class FixtureSummary(PublicModel):
    fixture_id: int
    competition_key: str | None = None
    league_id: int | None = None
    season: int | None = None
    round: str | None = None
    kickoff_at_utc: datetime | None = None
    kickoff_at_paris: datetime | None = None
    status_short: str | None = None
    status_long: str | None = None
    home_team: TeamSummary
    away_team: TeamSummary
    home_team_id: int | None = None
    away_team_id: int | None = None
    venue_name: str | None = None
    venue_city: str | None = None
    has_1x2_prediction: bool = False
    has_ou_prediction: bool = False
    has_combo: bool = False
    latest_prediction_time: datetime | None = None
    data_quality_score: float | None = None


class HealthResponse(PublicModel):
    status: str
    api_enabled: bool
    read_only: bool
    database_ok: bool
    app_timezone: str
    version: str
    timestamp: datetime


class VersionResponse(PublicModel):
    name: str
    version: str
    api_version: str
    read_only: bool


def safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(converted):
        return None
    return converted


def safe_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return _ensure_utc(datetime.fromisoformat(raw))
        except ValueError:
            return None
    return None


def paris_datetime(value: Any) -> datetime | None:
    parsed = safe_datetime(value)
    return parsed.astimezone(PARIS_TZ) if parsed is not None else None


def data_quality_score_from_json(payload: Any) -> float | None:
    if isinstance(payload, int | float | str):
        return safe_float(payload)
    if not isinstance(payload, dict):
        return None
    for key in (
        "data_quality_score",
        "score",
        "quality_score",
        "overall_score",
        "overall",
    ):
        value = safe_float(payload.get(key))
        if value is not None:
            return value
    nested = payload.get("data_quality")
    if isinstance(nested, dict):
        return data_quality_score_from_json(nested)
    return None


def data_quality_summary_from_json(payload: Any) -> DataQualitySummary:
    score = data_quality_score_from_json(payload)
    label = None
    if score is not None:
        if score >= 80:
            label = "High"
        elif score >= 60:
            label = "Medium"
        else:
            label = "Low"
    return DataQualitySummary(
        score=score,
        label=label,
        warnings=public_warnings_from_json(_warnings_payload(payload)),
    )


def public_warnings_from_json(payload: Any) -> list[PublicWarning]:
    warnings: list[PublicWarning] = []
    seen: set[str] = set()
    for code in _iter_warning_codes(payload):
        mapped = _PUBLIC_WARNING_MAP.get(code)
        if mapped is None:
            continue
        public_code, message, severity = mapped
        if public_code in seen:
            continue
        seen.add(public_code)
        warnings.append(PublicWarning(code=public_code, message=message, severity=severity))
    return warnings


def public_explanations_from_json(payload: Any, *, max_items: int = 8) -> list[str]:
    explanations: list[str] = []
    for item in _iter_explanation_items(payload):
        text = sanitize_text(str(item).strip())
        if not text or contains_sensitive_data(text):
            continue
        explanations.append(text[:220])
        if len(explanations) >= max_items:
            break
    return explanations


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _warnings_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    for key in ("warnings", "warnings_json", "warning_codes", "public_warnings"):
        if key in payload:
            return payload[key]
    return payload


def _iter_warning_codes(payload: Any) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        raw = payload.get("code") or payload.get("warning") or payload.get("reason")
        codes = [str(raw)] if raw else []
        for key in ("warnings", "warnings_json", "warning_codes", "reasons"):
            if key in payload:
                codes.extend(_iter_warning_codes(payload[key]))
        return codes
    if isinstance(payload, list | tuple | set):
        codes: list[str] = []
        for item in payload:
            codes.extend(_iter_warning_codes(item))
        return codes
    return []


def _iter_explanation_items(payload: Any) -> list[str]:
    if payload is None:
        return []
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        for key in ("public", "message", "text", "label", "reason"):
            value = payload.get(key)
            if isinstance(value, str):
                return [value]
        return []
    if isinstance(payload, list | tuple):
        items: list[str] = []
        for item in payload:
            items.extend(_iter_explanation_items(item))
        return items
    return []
