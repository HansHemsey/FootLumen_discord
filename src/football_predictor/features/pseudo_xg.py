"""Initial pseudo-xG heuristic for competitions without official xG."""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]


def heuristic_pseudo_xg(stats: JsonDict, penalties: int | float | None = None) -> float | None:
    """Approximate xG from shot profile.

    This is an initial availability signal, not official expected goals. It intentionally
    uses only common API-Football statistics and optional penalty events known before the
    prediction cutoff.
    """
    shots_on_goal = _number(stats.get("shots_on_goal"))
    shots_insidebox = _number(stats.get("shots_insidebox"))
    shots_outsidebox = _number(stats.get("shots_outsidebox"))
    total_shots = _number(stats.get("total_shots") or stats.get("shots_total"))
    penalty_count = _number(penalties) or _number(stats.get("penalties")) or 0.0

    has_shot_signal = any(
        value is not None
        for value in (shots_on_goal, shots_insidebox, shots_outsidebox, total_shots)
    )
    if not has_shot_signal and penalty_count == 0:
        return None

    return (
        0.03 * (total_shots or 0.0)
        + 0.09 * (shots_on_goal or 0.0)
        + 0.07 * (shots_insidebox or 0.0)
        + 0.02 * (shots_outsidebox or 0.0)
        + 0.76 * penalty_count
    )


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    cleaned = str(value).replace("%", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
