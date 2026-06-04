"""Domain objects for World Cup 2026 combo tickets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from football_predictor.world_cup_combos.enums import (
    ComboMarketScope,
    ComboMarketType,
    ComboTicketStatus,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupComboFixtureRef:
    fixture_id: int
    kickoff_at_utc: datetime
    kickoff_at_paris: datetime
    home_team: str
    away_team: str
    status_short: str | None
    round_name: str | None
    league_id: int
    season: int
    competition_key: str
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class WorldCupComboSession:
    session_key: str
    combo_date_paris: date
    first_kickoff_at: datetime
    last_kickoff_at: datetime
    fixtures: tuple[WorldCupComboFixtureRef, ...]
    stage: str
    group_matchday: int | None
    is_matchday3: bool
    is_knockout: bool
    lock_time: datetime
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboLegCandidate:
    fixture_id: int
    kickoff_at_utc: datetime
    market_type: ComboMarketType
    market_scope: ComboMarketScope
    selection: str
    decimal_odd: float
    model_probability: float
    market_probability: float
    edge: float
    ev: float
    confidence_score: float
    confidence_label: str
    data_quality_score: float
    odds_snapshot_id: int | None
    prediction_snapshot_id: int | None
    lineup_status: str
    odds_last_update: datetime | None
    prediction_generated_at: datetime | None
    kickoff_at_paris: datetime | None = None
    freshness_score: float | None = None
    no_candidate_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboFixtureNoCandidate:
    fixture_id: int
    session_key: str
    source_type: str
    reason: str
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboLegSelectionResult:
    sessions: tuple[WorldCupComboSession, ...] = field(default_factory=tuple)
    candidates: tuple[ComboLegCandidate, ...] = field(default_factory=tuple)
    no_candidates: tuple[ComboFixtureNoCandidate, ...] = field(default_factory=tuple)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboTicketCandidate:
    competition_key: str
    league_id: int
    season: int
    combo_date: date
    session_key: str
    ticket_key: str
    first_kickoff_at: datetime
    last_kickoff_at: datetime
    lock_time: datetime
    legs_count: int
    combined_decimal_odds: float
    combined_probability_raw: float
    combined_probability_adjusted: float
    combined_fair_odds: float
    combined_ev_raw: float
    combined_ev_adjusted: float
    combined_confidence_score: float
    combined_confidence_label: str
    post_lock_risk_score: float
    freshness_score: float
    lineup_risk_score: float
    publication_decision: ComboTicketStatus
    no_publish_reason: str | None
    legs: tuple[ComboLegCandidate, ...] = field(default_factory=tuple)
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboLegSnapshot:
    ticket_key: str
    leg_order: int
    candidate: ComboLegCandidate
    captured_at: datetime
    model_versions_json: JsonDict = field(default_factory=dict)
    warnings_json: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboTicketSnapshot:
    ticket_key: str
    status: ComboTicketStatus | str
    candidate: ComboTicketCandidate
    captured_at: datetime
    model_versions_json: JsonDict = field(default_factory=dict)
    warnings_json: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


@dataclass(frozen=True)
class ComboTicketDecision:
    ticket_key: str
    status: ComboTicketStatus
    publication_decision: ComboTicketStatus
    no_publish_reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_json_dict(self) -> JsonDict:
        return _json_dict(asdict(self))


def _json_dict(payload: JsonDict) -> JsonDict:
    return {key: _json_value(value) for key, value in payload.items()}


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (ComboTicketStatus, ComboMarketType, ComboMarketScope)):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value
