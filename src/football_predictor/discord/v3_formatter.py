"""French Discord formatter for V3 predictions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from football_predictor.discord.formatter import (
    CODE_CLOSE,
    CODE_OPEN,
    DISCORD_LIMIT,
    truncate_discord_message,
)
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.time import ensure_aware_utc

_UNAVAILABLE = "non disponible"
_SECRET_PATTERNS = (
    re.compile(r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\S+", re.I),
    re.compile(
        r"\b(?:api[_-]?key|api[_-]?football[_-]?key|token|secret)\s*[:=]\s*['\"]?[^'\"\s]+",
        re.I,
    ),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"),
)

_OUTCOMES = ("HOME", "DRAW", "AWAY")


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
    teams = _team_labels(prediction)
    outcome = _predicted_outcome(prediction, probabilities)

    lines = [
        CODE_OPEN,
        "🏟️ FOOT — PRÉDICTION V3 | M-30",
        f"{_clean(_field(prediction, 'match_label', _UNAVAILABLE))} · "
        f"{_clean(_field(prediction, 'competition', _UNAVAILABLE))}",
        _date_label(prediction, timezone_name),
        "",
        "🎯 PICK PRINCIPAL",
        f"▶ {_pick_label(outcome, teams)}",
        f"Confiance : {_confidence_label(prediction)} · Score : {_score_label(prediction)}",
        "",
        "📊 PROBABILITÉS",
        *_probability_table(teams, probabilities, market),
        "",
        "💡 LECTURE PARIEUR",
        *_bettor_reading(prediction, teams, outcome, probabilities, market),
    ]

    v2_lines = _v2_confirmation_lines(teams, probabilities, v2, outcome)
    if v2_lines:
        lines += ["", "🔁 CONFIRMATION V2 → V3", *v2_lines]

    lines += [
        "",
        "🧠 FACTEURS CLÉS",
        *_translated_factor_lines(prediction, teams),
        "",
        "👥 XI / ABSENCES",
        f"XI : {_lineup_label(prediction)}",
        *_absence_lines(prediction, teams),
        "",
        "✅ QUALITÉ DATA",
        *_data_quality_lines(_data_quality(prediction)),
        "",
        "⚠️ Modèle probabiliste à M-30, pas une certitude.",
        CODE_CLOSE,
    ]
    return truncate_discord_message("\n".join(lines), max_chars=limit)


def _date_label(prediction: Any, timezone_name: str) -> str:
    value = _field(prediction, "match_date", None)
    if isinstance(value, datetime):
        try:
            local = ensure_aware_utc(value).astimezone(ZoneInfo(timezone_name))
            return f"{local.strftime('%d/%m/%Y')} · {local.strftime('%H:%M')} {timezone_name}"
        except Exception:
            return _clean(value)
    if value is None:
        return _UNAVAILABLE
    return _clean(value)


def _team_labels(prediction: Any) -> dict[str, str]:
    match_label = _clean(_field(prediction, "match_label", "Domicile vs Extérieur"))
    if " vs " in match_label:
        home, away = match_label.split(" vs ", 1)
    elif " - " in match_label:
        home, away = match_label.split(" - ", 1)
    else:
        home, away = "Domicile", "Extérieur"
    return {
        "HOME": _short_label(home),
        "DRAW": "Nul",
        "AWAY": _short_label(away),
    }


def _short_label(value: Any, max_len: int = 15) -> str:
    text = _clean(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _predicted_outcome(prediction: Any, probabilities: ProbabilityTriple | None) -> str:
    outcome = _field(prediction, "predicted_result", None)
    if outcome is None and probabilities is not None:
        outcome = probabilities.predicted_result()
    outcome_text = str(outcome or "HOME").upper()
    return outcome_text if outcome_text in _OUTCOMES else "HOME"


def _pick_label(outcome: str, teams: Mapping[str, str]) -> str:
    if outcome == "DRAW":
        return "Match nul"
    return f"{teams[outcome]} gagne"


def _confidence_label(prediction: Any) -> str:
    label = _clean(_field(prediction, "confidence_label", _UNAVAILABLE))
    if label == _UNAVAILABLE:
        return label
    return label.upper().replace("_", " ")


def _score_label(prediction: Any) -> str:
    value = _numeric(_field(prediction, "confidence_score", None))
    return f"{value:.0f}/100" if value is not None else _UNAVAILABLE


def _probability_table(
    teams: Mapping[str, str],
    probabilities: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
) -> list[str]:
    lines = ["              Modèle   Marché   Écart"]
    for outcome in _OUTCOMES:
        model_value = _probability_value(probabilities, outcome)
        market_value = _probability_value(market, outcome)
        delta = None if model_value is None or market_value is None else model_value - market_value
        lines.append(
            f"{teams[outcome]:<13} "
            f"{_percent_cell(model_value):>7}  "
            f"{_percent_cell(market_value):>7}  "
            f"{_delta_cell(delta):>9}"
        )
    return lines


def _probability_value(probabilities: ProbabilityTriple | None, outcome: str) -> float | None:
    if probabilities is None:
        return None
    values = probabilities.normalized().as_dict()
    return values[outcome]


def _percent_cell(value: float | None) -> str:
    return "N/A" if value is None else _percent(value)


def _delta_cell(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f} pts"


def _bettor_reading(
    prediction: Any,
    teams: Mapping[str, str],
    outcome: str,
    probabilities: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
) -> list[str]:
    pick_target = teams[outcome] if outcome != "DRAW" else "nul"
    model_value = _probability_value(probabilities, outcome)
    market_value = _probability_value(market, outcome)
    edge = None if model_value is None or market_value is None else model_value - market_value
    draw_risk = _numeric(_field(prediction, "draw_risk_probability", None))
    draw_label = _clean(_field(prediction, "draw_risk_label", "non disponible"))
    home_no_draw = _numeric(_field(prediction, "home_no_draw_probability", None))
    away_no_draw = _numeric(_field(prediction, "away_no_draw_probability", None))
    draw_safety = _draw_safety_payload(prediction)

    lines = [_value_sentence(edge, pick_target)]
    lines.append(_market_sentence(probabilities, market))
    public_note = draw_safety.get("public_note") if isinstance(draw_safety, Mapping) else None
    if public_note:
        lines.append(f"• {_clean(public_note)}")
    if draw_risk is not None:
        lines.append(f"• Le nul reste un risque {draw_label} : {_percent(draw_risk)}.")
    no_draw = _no_draw_sentence(teams, home_no_draw, away_no_draw)
    if no_draw:
        lines.append(no_draw)
    return lines


def _value_sentence(edge: float | None, target: str) -> str:
    if edge is None:
        return f"• Le modèle identifie {target} comme scénario principal."
    if edge >= 0.10:
        return f"• Le modèle voit une forte value côté {target}."
    if edge >= 0.03:
        return f"• Le modèle voit une value modérée côté {target}."
    if edge <= -0.03:
        return f"• Le modèle est plus prudent que le marché sur {target}."
    return f"• Le modèle et le marché sont proches sur {target}."


def _market_sentence(
    probabilities: ProbabilityTriple | None,
    market: ProbabilityTriple | None,
) -> str:
    if probabilities is None or market is None:
        return "• Le marché est indisponible pour mesurer l'écart de value."
    model_values = probabilities.normalized().to_vector(_OUTCOMES)
    market_values = market.normalized().to_vector(_OUTCOMES)
    model_spread = max(model_values) - min(model_values)
    market_spread = max(market_values) - min(market_values)
    if model_spread > market_spread + 0.10:
        return "• Le marché est beaucoup plus équilibré que le modèle."
    if market_spread > model_spread + 0.10:
        return "• Le marché est plus tranché que le modèle."
    return "• Le marché ne contredit pas fortement le modèle."


def _no_draw_sentence(
    teams: Mapping[str, str],
    home_no_draw: float | None,
    away_no_draw: float | None,
) -> str | None:
    if home_no_draw is None and away_no_draw is None:
        return None
    home_value = home_no_draw or 0.0
    away_value = away_no_draw or 0.0
    if home_value >= away_value:
        side, value = teams["HOME"], home_value
    else:
        side, value = teams["AWAY"], away_value
    if value >= 0.60:
        return f"• Hors scénario de nul, avantage net {side} : {_percent(value)}."
    return (
        "• Hors scénario de nul, l'avantage reste équilibré : "
        f"{teams['HOME']} {_percent(home_value)} / {teams['AWAY']} {_percent(away_value)}."
    )


def _v2_confirmation_lines(
    teams: Mapping[str, str],
    probabilities: ProbabilityTriple | None,
    v2: ProbabilityTriple | None,
    outcome: str,
) -> list[str]:
    if probabilities is None or v2 is None:
        return []
    order = [outcome, "DRAW", *(item for item in _OUTCOMES if item not in {outcome, "DRAW"})]
    lines: list[str] = []
    for item in order:
        v2_value = _probability_value(v2, item)
        v3_value = _probability_value(probabilities, item)
        delta = None if v2_value is None or v3_value is None else v3_value - v2_value
        lines.append(
            f"{teams[item]:<10} : {_percent_cell(v2_value)} → {_percent_cell(v3_value)}"
            f"  ({_delta_cell(delta)})"
        )
    return lines


def _draw_safety_payload(prediction: Any) -> Mapping[str, Any]:
    payload = _field(prediction, "draw_safety_json", None)
    if isinstance(payload, Mapping):
        return payload
    payload = _field(prediction, "draw_safety", None)
    return payload if isinstance(payload, Mapping) else {}


def _translated_factor_lines(prediction: Any, teams: Mapping[str, str]) -> list[str]:
    factors: list[Any] = []
    for field_name in ("top_factors_draw_risk", "top_factors_no_draw_winner"):
        source = _field(prediction, field_name, None)
        if isinstance(source, Sequence) and not isinstance(source, str | bytes):
            factors.extend(source)

    lines: list[str] = []
    for factor in factors:
        sentence = _factor_sentence(factor, prediction, teams)
        if sentence and sentence not in lines:
            lines.append(sentence)
        if len(lines) >= 4:
            break
    return lines or ["• Les signaux modèle confirment la lecture principale."]


def _factor_sentence(
    factor: Any,
    prediction: Any,
    teams: Mapping[str, str],
) -> str:
    name = ""
    value: float | None = None
    if isinstance(factor, Mapping):
        name = str(factor.get("name", ""))
        value = _numeric(factor.get("value"))
    elif factor is not None:
        name = str(factor)

    key = name.lower()
    no_draw_team = _no_draw_team_label(prediction, teams)
    if "attacking_weakness" in key:
        return "• Les signaux offensifs faibles renforcent le risque de match serré."
    if "defensive_solidity" in key:
        return "• Les défenses récentes orientent vers un match potentiellement fermé."
    if "parity" in key:
        return "• Les équipes montrent des niveaux proches."
    if "xg_total_low" in key or "low_score" in key:
        return "• Le total de buts attendu reste modéré."
    if "xg_gap" in key:
        return "• L'écart xG pèse dans l'évaluation du risque de nul."
    if "market" in key and "draw" in key:
        return "• Le marché garde un signal notable sur le nul."
    if key.startswith("ndw_odds") or "odds_" in key:
        side = _side_from_factor_name(key, teams, fallback=no_draw_team)
        return f"• Les cotes marché soutiennent aussi l'option {side}."
    if "strength" in key or "ppg" in key:
        return f"• La dynamique globale avantage {no_draw_team}."
    if "attack_defense" in key:
        return f"• Le duel attaque/défense favorise {no_draw_team}."
    if "xi_value" in key:
        return f"• La valeur estimée du XI crée un avantage {no_draw_team}."
    if "absence" in key:
        return "• Les absences pèsent dans l'équilibre du match."
    if value is not None and value >= 0:
        return "• Un signal modèle complémentaire confirme la lecture principale."
    return "• Un signal modèle complémentaire appelle à rester prudent."


def _side_from_factor_name(key: str, teams: Mapping[str, str], *, fallback: str) -> str:
    if "away" in key:
        return teams["AWAY"]
    if "home" in key:
        return teams["HOME"]
    return fallback


def _no_draw_team_label(prediction: Any, teams: Mapping[str, str]) -> str:
    label = str(_field(prediction, "no_draw_winner_label", "")).lower()
    if label == "home":
        return teams["HOME"]
    if label == "away":
        return teams["AWAY"]
    home = _numeric(_field(prediction, "home_no_draw_probability", None)) or 0.0
    away = _numeric(_field(prediction, "away_no_draw_probability", None)) or 0.0
    if home > away:
        return teams["HOME"]
    if away > home:
        return teams["AWAY"]
    return "le côté le mieux coté"


def _lineup_label(prediction: Any) -> str:
    quality = _data_quality(prediction)
    if quality.get("official_lineup_available_flag") or quality.get("has_official_lineup"):
        return "officiel utilisé"
    return "probable, lineups officielles indisponibles"


def _absence_lines(prediction: Any, teams: Mapping[str, str]) -> list[str]:
    payload = _field(prediction, "key_absences_json", None)
    if not isinstance(payload, Mapping) or not payload:
        return ["Absences : non disponible avant prediction_time"]
    lines: list[str] = []
    for outcome, key in (("HOME", "home"), ("AWAY", "away")):
        items = payload.get(key)
        if not isinstance(items, Sequence) or isinstance(items, str | bytes):
            continue
        formatted = [_format_absence(item) for item in items[:3]]
        formatted = [item for item in formatted if item]
        if formatted:
            lines.append(f"{teams[outcome]} : " + ", ".join(formatted))
    return lines or ["Absences : non disponible avant prediction_time"]


def _format_absence(item: Any) -> str | None:
    if not isinstance(item, Mapping):
        return None
    name = _first_text(item, ("name", "player_name", "player", "label"))
    return _clean(name) if name is not None else None


def _data_quality(prediction: Any) -> dict[str, Any]:
    value = _field(prediction, "data_quality_json", None)
    return dict(value) if isinstance(value, Mapping) else {}


def _data_quality_lines(data_quality: Mapping[str, Any]) -> list[str]:
    score = _numeric(
        data_quality.get("overall_data_quality_score", data_quality.get("data_quality_score"))
    )
    return [
        f"Score : {score:.0f}/100" if score is not None else "Score : non disponible",
        "Odds : "
        f"{_yes_no_or_unavailable(data_quality.get('odds_available_flag'))}"
        " · Blessures : "
        f"{_yes_no_or_unavailable(data_quality.get('injuries_available_flag'))}"
        " · Stats joueurs : "
        f"{_yes_no_or_unavailable(_player_stats_quality_value(data_quality))}",
        "Lineups officielles : "
        f"{_yes_no_or_unavailable(_lineup_quality_value(data_quality))}",
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
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[secret masqué]", text)
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
