"""Availability and absence impact helpers for player/XI features."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from football_predictor.reference.lookups import PlayersReference

JsonDict = dict[str, Any]

POSITION_MULTIPLIERS = {
    "GK": 1.30,
    "DEF": 1.00,
    "MID": 1.00,
    "ATT": 1.25,
}


@dataclass(frozen=True)
class InjuryStatus:
    player_id: int
    severity: float
    reason: str | None
    type: str | None
    payload_json: JsonDict


def injury_severity(injury_type: str | None, reason: str | None = None) -> float:
    """Map API-Football injury labels to a conservative V1 severity."""
    return _severity_from_text(f"{injury_type or ''} {reason or ''}")


def parse_injury_severity(injury: Any) -> float:
    """Parse an API/DB injury object into the V1 severity scale."""
    if isinstance(injury, dict):
        injury_type = injury.get("type")
        reason = injury.get("reason")
    else:
        injury_type = getattr(injury, "type", None)
        reason = getattr(injury, "reason", None)
    return _severity_from_text(f"{injury_type or ''} {reason or ''}")


def compute_absence_impact(
    session: Session,
    team_id: int,
    fixture_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
) -> JsonDict:
    """Compute absence impact for one team in a target fixture."""
    from football_predictor.features.xi_features import build_player_xi_features

    result = build_player_xi_features(
        session,
        fixture_id,
        prediction_time,
        players_reference=players_reference,
    )
    target_team_prefix = _team_prefix(result.features_json, team_id)
    if target_team_prefix is None:
        return {
            "absent_expected_starters_count": 0,
            "absent_total_value": 0.0,
            "absence_impact_score": 0.0,
            "replacement_quality_score": 1.0,
            "availability_score": 1.0,
            "key_absences_json": [],
        }
    key_absences = result.features_json[f"{target_team_prefix}_key_absences_json"]
    absent_starters = [
        row
        for row in key_absences
        if float(row["p_start"]) >= 0.35 and float(row["severity"]) >= 0.5
    ]
    return {
        "absent_expected_starters_count": len(absent_starters),
        "absent_total_value": sum(float(row["player_value"]) for row in absent_starters),
        "absence_impact_score": result.features_json[f"{target_team_prefix}_absence_impact_score"],
        "replacement_quality_score": result.features_json[
            f"{target_team_prefix}_replacement_quality_score"
        ],
        "availability_score": result.features_json[f"{target_team_prefix}_availability_score"],
        "key_absences_json": key_absences,
    }


def _severity_from_text(text: str) -> float:
    label = text.casefold()
    if "missing fixture" in label or "suspended" in label or "suspension" in label:
        return 1.0
    if "doubtful" in label or "questionable" in label:
        return 0.6
    if "minor" in label or "mineur" in label:
        return 0.3
    return 0.3


def _team_prefix(features: JsonDict, team_id: int) -> str | None:
    home_team_id = features.get("home_team_id")
    away_team_id = features.get("away_team_id")
    if home_team_id == team_id:
        return "home_team"
    if away_team_id == team_id:
        return "away_team"
    return None


def position_multiplier(position_group: str, *, is_central_defender: bool = False) -> float:
    if position_group == "DEF" and is_central_defender:
        return 1.10
    return POSITION_MULTIPLIERS.get(position_group, 1.00)


def absence_impact(
    *,
    p_start: float,
    player_value: float,
    severity: float,
    replacement_gap: float,
    position_group: str,
    is_central_defender: bool = False,
) -> float:
    """Compute absence impact while damping likely non-starters."""
    effective_p_start = p_start if p_start >= 0.35 else p_start * 0.25
    return (
        effective_p_start
        * player_value
        * severity
        * max(replacement_gap, 0.0)
        * position_multiplier(position_group, is_central_defender=is_central_defender)
    )
