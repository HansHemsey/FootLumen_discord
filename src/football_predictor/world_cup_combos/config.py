"""Configuration for the World Cup 2026 combo ticket feature."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldCupComboConfig:
    enabled: bool = False
    competition_key: str = "fifa_world_cup_2026"
    league_id: int = 1
    season: int = 2026
    timezone_display: str = "Europe/Paris"
    max_public_legs: int = 2
    max_staff_legs: int = 3
    lock_buffer_minutes: int = 20
    max_session_span_hours_public: int = 4
    min_leg_ev: float = 0.03
    min_leg_edge: float = 0.03
    min_leg_data_quality: float = 65.0
    min_leg_confidence: float = 55.0
    min_combined_ev_adjusted: float = 0.03
    min_combined_confidence_public: float = 68.0
    max_post_lock_risk_public: float = 30.0
    require_positive_ev_each_leg: bool = True
    forbid_same_group_md3_multiple_legs: bool = True
    allow_public_matchday3: bool = False
    allow_public_knockout: bool = False
    staff_only_shadow_mode: bool = True

    def as_dict(self) -> JsonDict:
        return asdict(self)


def load_world_cup_combo_config(path: Path | str | None = None) -> WorldCupComboConfig:
    if path is None:
        return WorldCupComboConfig()
    config_path = Path(path)
    if not config_path.exists():
        return WorldCupComboConfig()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return WorldCupComboConfig()
    return world_cup_combo_config_from_mapping(payload)


def world_cup_combo_config_from_mapping(payload: JsonDict) -> WorldCupComboConfig:
    return WorldCupComboConfig(
        enabled=_bool(payload.get("enabled"), False),
        competition_key=str(payload.get("competition_key") or "fifa_world_cup_2026"),
        league_id=_int(payload.get("league_id"), 1),
        season=_int(payload.get("season"), 2026),
        timezone_display=str(payload.get("timezone_display") or "Europe/Paris"),
        max_public_legs=_int(payload.get("max_public_legs"), 2),
        max_staff_legs=_int(payload.get("max_staff_legs"), 3),
        lock_buffer_minutes=_int(payload.get("lock_buffer_minutes"), 20),
        max_session_span_hours_public=_int(payload.get("max_session_span_hours_public"), 4),
        min_leg_ev=_float(payload.get("min_leg_ev"), 0.03),
        min_leg_edge=_float(payload.get("min_leg_edge"), 0.03),
        min_leg_data_quality=_float(payload.get("min_leg_data_quality"), 65.0),
        min_leg_confidence=_float(payload.get("min_leg_confidence"), 55.0),
        min_combined_ev_adjusted=_float(payload.get("min_combined_ev_adjusted"), 0.03),
        min_combined_confidence_public=_float(
            payload.get("min_combined_confidence_public"),
            68.0,
        ),
        max_post_lock_risk_public=_float(payload.get("max_post_lock_risk_public"), 30.0),
        require_positive_ev_each_leg=_bool(
            payload.get("require_positive_ev_each_leg"),
            True,
        ),
        forbid_same_group_md3_multiple_legs=_bool(
            payload.get("forbid_same_group_md3_multiple_legs"),
            True,
        ),
        allow_public_matchday3=_bool(payload.get("allow_public_matchday3"), False),
        allow_public_knockout=_bool(payload.get("allow_public_knockout"), False),
        staff_only_shadow_mode=_bool(payload.get("staff_only_shadow_mode"), True),
    )


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
