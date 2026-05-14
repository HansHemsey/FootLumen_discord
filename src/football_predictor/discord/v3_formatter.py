"""French Discord formatter for V3 predictions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from football_predictor.discord.formatter import (
    CODE_CLOSE,
    CODE_OPEN,
    DISCORD_LIMIT,
    truncate_discord_message,
)
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.secrets import sanitize_secret_text
from football_predictor.utils.time import format_in_timezone

_UNAVAILABLE = "non disponible"

_OUTCOME_LABELS_FR = {
    "HOME": "Victoire domicile",
    "DRAW": "Match nul",
    "AWAY": "Victoire extérieur",
}


def format_prediction_v3_markdown(
    prediction: Any,
    *,
    timezone_name: str = "Europe/Paris",
    limit: int = DISCORD_LIMIT,
) -> str:
    """Format a V3 prediction as a Discord-safe markdown code block."""
    probabilities = _probabilities_from_prediction(prediction)
    market = _coerce_probabilities(_field(prediction, "market_probabilities", None))
    v2 = _coerce_probabilities(_field(prediction, "v2_probabilities", None))
    lines = [
        CODE_OPEN,
        "🏟️ PRÉDICTION FOOTBALL — V3",
        "",
        f"Match : {_clean(_field(prediction, 'match_label', _UNAVAILABLE))}",
        f"Compétition : {_clean(_field(prediction, 'competition', _UNAVAILABLE))}",
        f"Date : {_date_label(prediction, timezone_name)}",
        "Fenêtre : M-30 (kickoff - 30 min)",
        "",
        f"Résultat prédit : {_outcome_label(prediction, probabilities)}",
        f"Confiance : {_clean(_field(prediction, 'confidence_label', _UNAVAILABLE))}",
        f"Score de confiance : {_score_label(prediction)}",
        "",
        "Probabilités modèle V3 (finales) :",
        *_probability_lines(probabilities),
        "",
        "Décomposition V3 :",
        f"- Risque de nul        : {_component_percent(prediction, 'draw_risk_probability')}"
        f" ({_clean(_field(prediction, 'draw_risk_label', _UNAVAILABLE))})",
        f"- Avantage hors nul    : {_no_draw_advantage_line(prediction)}",
        "",
        *_source_lines("Probabilités marché", market),
        "",
        *_v2_lines(v2),
        "",
        "Top facteurs (Risque de nul) :",
        *_factor_lines(_field(prediction, "top_factors_draw_risk", None)),
        "",
        "Top facteurs (Hors nul -> "
        f"{_clean(_field(prediction, 'no_draw_winner_label', 'équilibré'))}) :",
        *_factor_lines(_field(prediction, "top_factors_no_draw_winner", None)),
        "",
        "XI :",
        f"- {_lineup_label(prediction)}",
        "",
        "Absences clés :",
        *_absence_lines(_field(prediction, "key_absences_json", None)),
        "",
        "Qualité des données :",
        *_data_quality_lines(_data_quality(prediction)),
        "",
        "Note : prédiction probabiliste à M-30, pas une certitude.",
        CODE_CLOSE,
    ]
    return truncate_discord_message("\n".join(lines), max_chars=limit)


def _date_label(prediction: Any, timezone_name: str) -> str:
    value = _field(prediction, "match_date", None)
    if value is None:
        return _UNAVAILABLE
    if hasattr(value, "astimezone"):
        return f"{format_in_timezone(value, timezone_name)} {timezone_name}"
    return _clean(value)


def _outcome_label(prediction: Any, probabilities: ProbabilityTriple | None) -> str:
    outcome = _field(prediction, "predicted_result", None)
    if outcome is None and probabilities is not None:
        outcome = probabilities.predicted_result()
    if outcome is None:
        return _UNAVAILABLE
    return _OUTCOME_LABELS_FR.get(str(outcome).upper(), _clean(outcome))


def _score_label(prediction: Any) -> str:
    value = _numeric(_field(prediction, "confidence_score", None))
    return f"{value:.1f} pts" if value is not None else _UNAVAILABLE


def _component_percent(prediction: Any, field_name: str) -> str:
    value = _numeric(_field(prediction, field_name, None))
    return _percent(value) if value is not None else _UNAVAILABLE


def _no_draw_advantage_line(prediction: Any) -> str:
    home = _numeric(_field(prediction, "home_no_draw_probability", None))
    away = _numeric(_field(prediction, "away_no_draw_probability", None))
    label = _clean(_field(prediction, "no_draw_winner_label", _UNAVAILABLE))
    if home is None and away is None:
        return _UNAVAILABLE
    if label == "Home":
        return f"Home ({_percent(home or 0.0)})"
    if label == "Away":
        return f"Away ({_percent(away or 0.0)})"
    return f"équilibré (Home {_percent(home or 0.0)} / Away {_percent(away or 0.0)})"


def _probability_lines(probabilities: ProbabilityTriple | None) -> list[str]:
    if probabilities is None:
        return [
            "- Domicile  : non disponible",
            "- Nul       : non disponible",
            "- Extérieur : non disponible",
        ]
    normalized = probabilities.normalized()
    return [
        f"- Domicile  : {_percent(normalized.p_home)}",
        f"- Nul       : {_percent(normalized.p_draw)}",
        f"- Extérieur : {_percent(normalized.p_away)}",
    ]


def _source_lines(title: str, probabilities: ProbabilityTriple | None) -> list[str]:
    if probabilities is None:
        return [f"{title} : non disponible"]
    return [f"{title} :", *_probability_lines(probabilities)]


def _v2_lines(probabilities: ProbabilityTriple | None) -> list[str]:
    if probabilities is None:
        return []
    return ["Comparaison V2 :", *_probability_lines(probabilities)]


def _factor_lines(factors: Any) -> list[str]:
    if not isinstance(factors, Sequence) or isinstance(factors, str | bytes):
        return ["1. non disponible"]
    lines: list[str] = []
    for index, item in enumerate(factors[:3], start=1):
        if isinstance(item, Mapping):
            name = _clean(item.get("name", _UNAVAILABLE))
            value = _numeric(item.get("value"))
            suffix = f" ({value:.2f})" if value is not None else ""
            lines.append(f"{index}. {name}{suffix}")
        elif str(item).strip():
            lines.append(f"{index}. {_clean(item)}")
    return lines or ["1. non disponible"]


def _lineup_label(prediction: Any) -> str:
    quality = _data_quality(prediction)
    if quality.get("official_lineup_available_flag") or quality.get("has_official_lineup"):
        return "XI officiel utilisé"
    return "XI probable utilisé, lineups officielles indisponibles"


def _absence_lines(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping) or not payload:
        return ["- non disponible avant prediction_time"]
    lines: list[str] = []
    for label, key in (("Home", "home"), ("Away", "away")):
        items = payload.get(key)
        if not isinstance(items, Sequence) or isinstance(items, str | bytes):
            continue
        formatted = [_format_absence(item) for item in items[:3]]
        formatted = [item for item in formatted if item]
        if formatted:
            lines.append(f"- {label} : " + "; ".join(formatted))
    return lines or ["- non disponible avant prediction_time"]


def _format_absence(item: Any) -> str | None:
    if not isinstance(item, Mapping):
        return None
    name = _first_text(item, ("name", "player_name", "player", "label"))
    reason = _first_text(item, ("reason", "type", "status"))
    if name is None:
        return None
    if reason and reason != name:
        return f"{_clean(name)} ({_clean(reason)})"
    return _clean(name)


def _data_quality(prediction: Any) -> dict[str, Any]:
    value = _field(prediction, "data_quality_json", None)
    return dict(value) if isinstance(value, Mapping) else {}


def _data_quality_lines(data_quality: Mapping[str, Any]) -> list[str]:
    score = _numeric(
        data_quality.get("overall_data_quality_score", data_quality.get("data_quality_score"))
    )
    return [
        f"- Score global : {score:.0f}/100"
        if score is not None
        else "- Score global : non disponible",
        f"- Odds : {_yes_no_or_unavailable(data_quality.get('odds_available_flag'))}",
        f"- Lineups officielles : {_yes_no_or_unavailable(_lineup_quality_value(data_quality))}",
        f"- Blessures : {_yes_no_or_unavailable(data_quality.get('injuries_available_flag'))}",
        "- Stats joueurs : "
        f"{_yes_no_or_unavailable(_player_stats_quality_value(data_quality))}",
    ]


def _lineup_quality_value(data_quality: Mapping[str, Any]) -> Any:
    return (
        data_quality.get("official_lineup_available_flag")
        if "official_lineup_available_flag" in data_quality
        else data_quality.get("has_official_lineup")
    )


def _player_stats_quality_value(data_quality: Mapping[str, Any]) -> Any:
    if "player_stats_available_flag" in data_quality:
        return data_quality["player_stats_available_flag"]
    rate = _numeric(
        data_quality.get(
            "historical_player_stats_available_rate",
            data_quality.get("player_stats_available_rate"),
        )
    )
    return None if rate is None else rate > 0


def _probabilities_from_prediction(prediction: Any) -> ProbabilityTriple | None:
    explicit = _coerce_probabilities(_field(prediction, "probabilities", None))
    return explicit if explicit is not None else _coerce_probabilities(prediction)


def _coerce_probabilities(value: Any) -> ProbabilityTriple | None:
    if value is None:
        return None
    if isinstance(value, ProbabilityTriple):
        return value.normalized()
    if isinstance(value, Mapping):
        try:
            return ProbabilityTriple.from_mapping(value)
        except ValueError:
            return None
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        try:
            return ProbabilityTriple.from_vector([float(item) for item in value[:3]])
        except (TypeError, ValueError):
            return None
    values = {
        "p_home": _field(value, "p_home", None),
        "p_draw": _field(value, "p_draw", None),
        "p_away": _field(value, "p_away", None),
    }
    if all(item is not None for item in values.values()):
        try:
            return ProbabilityTriple.from_mapping(values)
        except ValueError:
            return None
    return None


def _field(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _first_text(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "reason", "type"))
            if nested:
                return nested
        elif value is not None and str(value).strip():
            return str(value)
    return None


def _clean(value: Any) -> str:
    text = str(value).replace("```", "'''").replace("\r", " ").strip()
    text = sanitize_secret_text(text, replacement="[secret masqué]")
    return " ".join(text.split()) or _UNAVAILABLE


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _yes_no_or_unavailable(value: Any) -> str:
    if value is None:
        return _UNAVAILABLE
    return "oui" if bool(value) else "non"
