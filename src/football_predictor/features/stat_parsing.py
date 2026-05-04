"""Parsing helpers for API-Football fixture statistics."""

from __future__ import annotations

from typing import Any

from football_predictor.features.pseudo_xg import heuristic_pseudo_xg

JsonDict = dict[str, Any]


def _normalize_label(value: Any) -> str:
    return " ".join(str(value).strip().casefold().replace("-", " ").split())


STAT_ALIASES: dict[str, set[str]] = {
    "shots_on_goal": {"shots on goal", "shots on target"},
    "shots_off_goal": {"shots off goal", "shots off target"},
    "shots_insidebox": {"shots insidebox", "shots inside box", "shots inside the box"},
    "shots_outsidebox": {"shots outsidebox", "shots outside box", "shots outside the box"},
    "total_shots": {"total shots", "shots total", "shots"},
    "blocked_shots": {"blocked shots"},
    "fouls": {"fouls"},
    "corners": {"corner kicks", "corners"},
    "offsides": {"offsides"},
    "possession": {"ball possession", "possession"},
    "yellow_cards": {"yellow cards", "yellow card"},
    "red_cards": {"red cards", "red card"},
    "goalkeeper_saves": {"goalkeeper saves", "keeper saves", "saves"},
    "passes_total": {"total passes", "passes total", "passes"},
    "passes_accurate": {"passes accurate", "accurate passes", "passes completed"},
    "passes_percentage": {"passes %", "pass %", "passes percentage", "pass accuracy"},
}

NORMALIZED_STAT_LABELS = {
    _normalize_label(label): metric
    for metric, aliases in STAT_ALIASES.items()
    for label in aliases
}

STAT_KEYS = tuple(STAT_ALIASES.keys())


def parse_fixture_statistics(statistics_json: Any, *, penalties: int = 0) -> JsonDict:
    """Parse API-Football statistics rows into stable numeric keys."""
    stats: JsonDict = {metric: None for metric in STAT_KEYS}
    for item in _items(statistics_json):
        label = _normalize_label(item.get("type") or item.get("name") or "")
        metric = NORMALIZED_STAT_LABELS.get(label)
        if metric is None:
            continue
        value = parse_stat_number(item.get("value"))
        if value is not None:
            stats[metric] = value

    stats["shots_total"] = stats["total_shots"]
    stats["shots_inside_box"] = stats["shots_insidebox"]
    stats["shots_outside_box"] = stats["shots_outsidebox"]
    stats["pass_accuracy"] = stats["passes_percentage"]
    stats["cards"] = _sum_available(stats.get("yellow_cards"), stats.get("red_cards"))
    stats["pseudo_xg"] = heuristic_pseudo_xg(stats, penalties=penalties)
    return stats


def parse_stat_number(value: Any) -> float | None:
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


def _items(statistics_json: Any) -> list[JsonDict]:
    if isinstance(statistics_json, list):
        return [item for item in statistics_json if isinstance(item, dict)]
    if isinstance(statistics_json, dict):
        return [{"type": key, "value": value} for key, value in statistics_json.items()]
    return []


def _sum_available(*values: Any) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric)
