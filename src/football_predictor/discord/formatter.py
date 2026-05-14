"""French markdown formatter for Discord predictions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.secrets import sanitize_secret_text
from football_predictor.utils.time import format_in_timezone

DISCORD_LIMIT = 1900
CODE_OPEN = "```md"
CODE_CLOSE = "```"
TRUNCATION_MARKER = "... message tronqué ..."

_UNAVAILABLE = "non disponible"
_OUTCOME_LABELS_FR = {
    "HOME": "victoire domicile",
    "DRAW": "match nul",
    "AWAY": "victoire extérieur",
}


def format_prediction_markdown(
    prediction: Any,
    fixture: Any | None = None,
    features: Mapping[str, Any] | None = None,
    *,
    timezone_name: str = "Europe/Paris",
    limit: int = DISCORD_LIMIT,
) -> str:
    """Format a prediction as a closed Discord-safe markdown code block.

    The preferred Sprint 14 API is ``format_prediction_markdown(prediction, fixture,
    features=None)``. For compatibility with the existing CLI, passing a timezone string
    as the second positional argument is still accepted.
    """
    if isinstance(fixture, str) and features is None and timezone_name == "Europe/Paris":
        timezone_name = fixture
        fixture = None

    model_probabilities = _probabilities_from_prediction(prediction)
    market_probabilities = _market_probabilities(prediction, features)
    data_quality = _data_quality(prediction)

    lines = [
        CODE_OPEN,
        "🏟️ PRÉDICTION FOOTBALL",
        "",
        f"Match : {_match_label(prediction, fixture)}",
        f"Compétition : {_competition_label(prediction, fixture)}",
        f"Date : {_date_label(prediction, fixture, timezone_name)}",
        "",
        f"Résultat prédit : {_outcome_label(prediction)}",
        f"Confiance : {_confidence_label(prediction)}",
        f"Score de confiance : {_score_label(prediction)}",
        f"Écart de confiance : {_gap_label(model_probabilities)}",
        "",
        "Probabilités modèle :",
        *_probability_lines(model_probabilities),
        "",
        *_market_lines(market_probabilities),
        "",
        "Facteurs clés :",
        *_explanation_lines(_field(prediction, "explanations", None)),
        "",
        "Absences clés :",
        *_absence_lines(_key_absences(prediction, features)),
        "",
        "Qualité des données :",
        *_data_quality_lines(data_quality),
        "",
        "Note : prédiction probabiliste, pas une certitude.",
        CODE_CLOSE,
    ]
    return truncate_discord_message("\n".join(lines), max_chars=limit)


def truncate_discord_message(message: str, max_chars: int = DISCORD_LIMIT) -> str:
    """Truncate line-by-line while preserving a valid markdown code fence."""
    if max_chars < len(CODE_OPEN) + len(CODE_CLOSE) + 3:
        raise ValueError("max_chars is too small to contain a closed markdown code block")
    closed = _ensure_closed_block(message)
    if len(closed) <= max_chars:
        return closed

    body = closed
    if body.startswith(CODE_OPEN):
        body = body[len(CODE_OPEN) :].lstrip("\n")
    if body.endswith("\n" + CODE_CLOSE):
        body = body[: -len("\n" + CODE_CLOSE)]
    elif body.endswith(CODE_CLOSE):
        body = body[: -len(CODE_CLOSE)].rstrip("\n")

    prefix = CODE_OPEN + "\n"
    suffix = "\n" + TRUNCATION_MARKER + "\n" + CODE_CLOSE
    available = max(0, max_chars - len(prefix) - len(suffix))
    kept: list[str] = []
    used = 0
    for line in body.splitlines():
        candidate_len = len(line) if not kept else len(line) + 1
        if used + candidate_len > available:
            break
        kept.append(line)
        used += candidate_len

    if not kept and available > 0:
        cut = body[:available].rsplit("\n", maxsplit=1)[0] or body[:available]
        kept.append(cut.rstrip())

    truncated_body = "\n".join(kept).rstrip()
    return prefix + truncated_body + suffix


def truncate_markdown_block(markdown: str, limit: int = DISCORD_LIMIT) -> str:
    """Backward-compatible alias for older callers."""
    return truncate_discord_message(markdown, max_chars=limit)


def _ensure_closed_block(markdown: str) -> str:
    if markdown.startswith(CODE_OPEN) and markdown.endswith("\n" + CODE_CLOSE):
        return markdown
    if markdown.startswith(CODE_OPEN) and markdown.endswith(CODE_CLOSE):
        return markdown.rstrip()
    return markdown.rstrip("` \n") + "\n" + CODE_CLOSE


def _match_label(prediction: Any, fixture: Any | None) -> str:
    value = _field(prediction, "match_label", None)
    if value:
        return _clean(value)
    home = _first_available(
        fixture,
        ("home_team_name", "home_name", "home_team", "home"),
    )
    away = _first_available(
        fixture,
        ("away_team_name", "away_name", "away_team", "away"),
    )
    if home and away:
        return f"{_clean(home)} vs {_clean(away)}"
    return _UNAVAILABLE


def _competition_label(prediction: Any, fixture: Any | None) -> str:
    value = _field(prediction, "competition", None)
    if value:
        return _clean(value)
    value = _first_available(fixture, ("competition", "league_name", "league", "name"))
    return _clean(value) if value else _UNAVAILABLE


def _date_label(prediction: Any, fixture: Any | None, timezone_name: str) -> str:
    value = _field(prediction, "match_date", None) or _field(fixture, "date", None)
    if value is None:
        return _UNAVAILABLE
    if isinstance(value, datetime):
        return f"{format_in_timezone(value, timezone_name)} {timezone_name}"
    return _clean(value)


def _outcome_label(prediction: Any) -> str:
    outcome = _field(prediction, "predicted_outcome", None) or _field(
        prediction,
        "predicted_result",
        None,
    )
    if outcome is None:
        probabilities = _probabilities_from_prediction(prediction)
        if probabilities is not None:
            outcome = probabilities.predicted_result()
    if outcome is None:
        return _UNAVAILABLE
    return _OUTCOME_LABELS_FR.get(str(outcome).upper(), _clean(outcome))


def _score_label(prediction: Any) -> str:
    value = _numeric(_field(prediction, "confidence_score", None))
    return f"{value:.1f} pts" if value is not None else _UNAVAILABLE


def _confidence_label(prediction: Any) -> str:
    value = _field(prediction, "confidence_label", None)
    return _clean(value) if value is not None else _UNAVAILABLE


def _gap_label(probabilities: ProbabilityTriple | None) -> str:
    if probabilities is None:
        return _UNAVAILABLE
    values = sorted(probabilities.to_vector(), reverse=True)
    return f"{(values[0] - values[1]) * 100:.1f} pts"


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


def _market_lines(market_probabilities: ProbabilityTriple | None) -> list[str]:
    if market_probabilities is None:
        return ["Probabilités marché : non disponible"]
    return ["Probabilités marché :", *_probability_lines(market_probabilities)]


def _explanation_lines(explanations: Any) -> list[str]:
    if not isinstance(explanations, Sequence) or isinstance(explanations, str | bytes):
        return ["1. non disponible"]
    cleaned = [_clean(text) for text in explanations[:3] if str(text).strip()]
    if not cleaned:
        return ["1. non disponible"]
    return [f"{index}. {text}" for index, text in enumerate(cleaned, start=1)]


def _absence_lines(payload: Mapping[str, Any] | None) -> list[str]:
    if not payload:
        return ["- non disponible avant prediction_time"]
    lines: list[str] = []
    for label, keys in (
        ("Domicile", ("home", "home_team", "home_absences")),
        ("Extérieur", ("away", "away_team", "away_absences")),
    ):
        items = _first_mapping_value(payload, keys)
        if not isinstance(items, Sequence) or isinstance(items, str | bytes):
            continue
        formatted = [item for item in (_format_absence(item) for item in items[:3]) if item]
        if formatted:
            lines.append(f"- {label} : " + "; ".join(formatted))
    return lines or ["- non disponible avant prediction_time"]


def _format_absence(item: Any) -> str | None:
    if not isinstance(item, Mapping):
        return None
    name = _first_text(item, ("name", "player_name", "player", "label"))
    reason = _first_text(item, ("reason", "type", "status"))
    impact = _numeric(
        item.get("absence_impact")
        or item.get("absence_impact_score")
        or item.get("impact")
    )
    if name is None:
        return None
    parts = [_clean(name)]
    if reason and reason != name:
        parts.append(f"({_clean(reason)})")
    if impact is not None:
        parts.append(f"impact {impact:.2f}")
    return " ".join(str(part) for part in parts)


def _data_quality(prediction: Any) -> dict[str, Any]:
    quality_json = _field(prediction, "data_quality_json", None)
    data_quality = _field(prediction, "data_quality", None)
    result: dict[str, Any] = {}
    if isinstance(quality_json, Mapping):
        result.update(quality_json)
    if "overall_data_quality_score" not in result and hasattr(data_quality, "score"):
        result["overall_data_quality_score"] = data_quality.score()

    bool_fields = {
        "odds_available": ("odds_available", "market_available", "odds_available_flag"),
        "injuries_available": ("injuries_available", "injuries_available_flag"),
        "target_lineups_available": (
            "target_lineups_available",
            "target_lineups_available_flag",
            "official_lineups_available",
        ),
        "historical_lineups_available": (
            "historical_lineups_available",
            "historical_lineups_available_flag",
            "lineups_available_flag",
            "official_lineups_available",
        ),
        "historical_player_stats_available": (
            "historical_player_stats_available",
            "player_stats_available_flag",
            "player_stats_available",
        ),
    }
    for output_key, aliases in bool_fields.items():
        if output_key in result:
            continue
        value = _first_available(data_quality, aliases)
        if value is not None:
            result[output_key] = bool(value)
    if "historical_player_stats_available" not in result:
        rate = _numeric(
            result.get("historical_player_stats_available_rate")
            if "historical_player_stats_available_rate" in result
            else result.get("player_stats_available_rate")
        )
        if rate is not None:
            result["historical_player_stats_available"] = rate > 0
    return result


def _data_quality_lines(data_quality: Mapping[str, Any]) -> list[str]:
    score = _numeric(data_quality.get("overall_data_quality_score"))
    score_label = f"{score:.0f}/100" if score is not None else _UNAVAILABLE
    return [
        f"- Score global : {score_label}",
        f"- Odds : {_yes_no_or_unavailable(data_quality.get('odds_available'))}",
        f"- Blessures : {_yes_no_or_unavailable(data_quality.get('injuries_available'))}",
        "- Lineups officielles cible : "
        f"{_yes_no_or_unavailable(data_quality.get('target_lineups_available'))}",
        "- Historique lineups : "
        f"{_yes_no_or_unavailable(data_quality.get('historical_lineups_available'))}",
        "- Stats joueurs historiques : "
        f"{_yes_no_or_unavailable(data_quality.get('historical_player_stats_available'))}",
    ]


def _probabilities_from_prediction(prediction: Any) -> ProbabilityTriple | None:
    explicit = _coerce_probabilities(_field(prediction, "probabilities", None))
    if explicit is not None:
        return explicit
    return _coerce_probabilities(prediction)


def _market_probabilities(
    prediction: Any,
    features: Mapping[str, Any] | None,
) -> ProbabilityTriple | None:
    explicit = _coerce_probabilities(_field(prediction, "market_probabilities", None))
    if explicit is not None:
        return explicit
    if not isinstance(features, Mapping):
        return None
    for keys in (
        ("p_market_home", "p_market_draw", "p_market_away"),
        ("market_home", "market_draw", "market_away"),
    ):
        values = {
            label: features.get(key)
            for label, key in zip(("home", "draw", "away"), keys, strict=True)
        }
        if all(value is not None for value in values.values()):
            return _coerce_probabilities(values)
    return None


def _key_absences(prediction: Any, features: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    payload = _field(prediction, "key_absences_json", None)
    if isinstance(payload, Mapping) and payload:
        return payload
    if not isinstance(features, Mapping):
        return None
    home = features.get("home_team_key_absences_json")
    away = features.get("away_team_key_absences_json")
    if home or away:
        return {"home": home or [], "away": away or []}
    return None


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


def _first_available(source: Any, keys: Sequence[str]) -> Any:
    for key in keys:
        value = _field(source, key, None)
        if value is not None and str(value).strip():
            return value
    return None


def _first_mapping_value(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _clean(value: Any) -> str:
    text = str(value).replace("```", "'''").replace("\r", " ").strip()
    text = sanitize_secret_text(text, replacement="[secret masqué]")
    return " ".join(text.split()) or _UNAVAILABLE


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
