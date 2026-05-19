"""Discord markdown formatter for O/U 2.5 predictions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from football_predictor.utils.time import ensure_aware_utc

DISCORD_LIMIT = 1900
CODE_OPEN = "```md"
CODE_CLOSE = "```"
_TRUNCATION = "... message tronqué ..."
_NA = "N/A"
_SECRET_PATTERNS = (
    re.compile(r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\S+", re.I),
    re.compile(
        r"\b(?:api[_-]?key|api[_-]?football[_-]?key|token|secret)\s*[:=]\s*['\"]?[^'\"\s]+",
        re.I,
    ),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"),
)


def format_ou_prediction_markdown(
    prediction: Any,
    fixture: Any | None = None,
    *,
    timezone_name: str = "Europe/Paris",
    limit: int = DISCORD_LIMIT,
    edge_display_threshold: float = 0.02,
) -> str:
    """Format an OUPredictionOutput as a Discord-safe markdown code block."""
    p_over = _number(getattr(prediction, "p_over", None), default=0.5)
    p_under = _number(getattr(prediction, "p_under", None), default=1.0 - p_over)
    forecast_side = _side(
        getattr(prediction, "forecast_side", None),
        fallback="OVER" if p_over >= p_under else "UNDER",
    )
    value_side = _side(getattr(prediction, "value_side", None), fallback=None)
    legacy_pick = value_side is None and getattr(prediction, "no_bet_reason", None) is None
    pick_side = value_side or (forecast_side if legacy_pick else None)
    forecast = _side_label(forecast_side)
    pick = _side_label(pick_side) if pick_side is not None else "No bet"

    market_p_over = _number(getattr(prediction, "market_p_over", None))
    market_p_under = _number(getattr(prediction, "market_p_under", None))
    edge_over = _number(getattr(prediction, "edge_over", None))
    edge_under = _number(getattr(prediction, "edge_under", None))
    ev_over = _number(getattr(prediction, "ev_over", None))
    ev_under = _number(getattr(prediction, "ev_under", None))
    pick_edge = _number(getattr(prediction, "value_edge", None))
    if pick_edge is None and pick_side is not None:
        pick_edge = edge_over if pick_side == "OVER" else edge_under
    pick_ev = _number(getattr(prediction, "value_ev", None))
    if pick_ev is None and pick_side is not None:
        pick_ev = ev_over if pick_side == "OVER" else ev_under
    no_bet_reason = getattr(prediction, "no_bet_reason", None)
    non_publication_reason = getattr(prediction, "non_publication_reason", None)
    pick_probability = _number(getattr(prediction, "p_pick", None))
    if pick_probability is None and pick_side is not None:
        pick_probability = p_over if pick_side == "OVER" else p_under
    pick_market_probability = _number(getattr(prediction, "market_p_pick", None))
    if pick_market_probability is None and pick_side is not None:
        pick_market_probability = market_p_over if pick_side == "OVER" else market_p_under
    pick_odd = _number(getattr(prediction, "odd_pick", None))
    if pick_odd is None and pick_side is not None:
        pick_odd = (
            _number(getattr(prediction, "market_odd_over", None))
            if pick_side == "OVER"
            else _number(getattr(prediction, "market_odd_under", None))
        )
    data_quality_score = _data_quality_score(getattr(prediction, "data_quality_json", None))

    lines = [
        CODE_OPEN,
        "⚽ FOOT — PRÉDICTION O/U 2.5 | M-30",
        f"{_match_label(prediction, fixture)} · {_competition_label(prediction, fixture)}",
        _date_str(_kickoff_time(prediction, fixture), timezone_name),
        "",
        "🎯 SCÉNARIO MODÈLE",
        f"Scénario le plus probable : {forecast} — "
        f"{_pct(p_over if forecast_side == 'OVER' else p_under)}",
        "",
        "💰 PICK VALUE",
    ]
    if pick_side is None:
        lines += [
            "Aucun pick public",
            f"Raison : {_reason_label(no_bet_reason or non_publication_reason)}",
        ]
    else:
        lines += [
            f"Côté : {pick}",
            f"Probabilité modèle : {_pct(pick_probability)}",
            f"Probabilité marché : {_pct(pick_market_probability)}",
            f"Cote utilisée : {_odd_str(pick_odd)}",
            f"Edge : {_delta_str(pick_edge)}",
            f"EV : {_ev_str(pick_ev)}",
            f"Confiance V2 : {_score_label(prediction)} · {_confidence_label(prediction)}",
            f"Data quality : {_quality_score_str(data_quality_score)}",
        ]
        if non_publication_reason:
            lines.append(f"Publication : staff · {_reason_label(non_publication_reason)}")
        else:
            lines.append("Publication : public")
    lines += [
        "",
        "📊 PROBABILITÉS",
        "              Modèle   Marché   Écart",
        _ou_probability_row("Plus 2.5", p_over, market_p_over),
        _ou_probability_row("Moins 2.5", p_under, market_p_under),
        "",
        "💡 LECTURE PARIEUR",
        _value_sentence(pick, pick_edge, no_bet_reason=no_bet_reason),
        _market_sentence(market_p_over, market_p_under),
        f"• xG attendu : {_xg_str(prediction)}.",
    ]

    if no_bet_reason:
        lines.append(f"• Raison no bet : {_reason_label(no_bet_reason)}.")
    if pick_side is not None and pick_edge is not None and abs(pick_edge) >= edge_display_threshold:
        lines.append(f"• Edge du pick : {_delta_str(pick_edge)}.")
    if pick_side is not None and pick_ev is not None:
        lines.append(f"• EV estimée : {_ev_str(pick_ev)} / unité.")

    quality_lines = _data_quality_lines(getattr(prediction, "data_quality_json", None))
    if quality_lines:
        lines += ["", "✅ QUALITÉ DATA", *quality_lines]

    lines += ["", "⚠️ Modèle probabiliste à M-30, pas une certitude.", CODE_CLOSE]
    return _truncate("\n".join(lines), limit)


def _ou_probability_row(label: str, model_value: float | None, market_value: float | None) -> str:
    delta = None if model_value is None or market_value is None else model_value - market_value
    return (
        f"{label:<13} "
        f"{_pct(model_value):>7}  "
        f"{_pct(market_value):>7}  "
        f"{_delta_str(delta):>9}"
    )


def _value_sentence(pick: str, edge: float | None, *, no_bet_reason: Any = None) -> str:
    target = pick.lower()
    if no_bet_reason:
        return "• Aucun pick value publiable n'est identifié sur cette ligne."
    if edge is None:
        return f"• Le modèle identifie {target} comme scénario principal."
    if edge >= 0.10:
        return f"• Le modèle voit une forte value côté {target}."
    if edge >= 0.03:
        return f"• Le modèle voit une value modérée côté {target}."
    if edge <= -0.03:
        return f"• Le modèle est plus prudent que le marché sur {target}."
    return f"• Le modèle et le marché sont proches sur {target}."


def _market_sentence(market_p_over: float | None, market_p_under: float | None) -> str:
    if market_p_over is None or market_p_under is None:
        return "• Le marché O/U est indisponible pour mesurer la value."
    if abs(market_p_over - market_p_under) <= 0.08:
        return "• Le marché est très équilibré sur la ligne 2.5."
    side = "Plus 2.5" if market_p_over > market_p_under else "Moins 2.5"
    return f"• Le marché penche plutôt côté {side}."


def _data_quality_lines(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping) or not payload:
        return []
    score = _data_quality_score(payload)
    lines = [f"Score : {score:.0f}/100" if score is not None else "Score : N/A"]
    odds_available = payload.get("ou_odds_available")
    if odds_available is None:
        odds_available = payload.get("odds_available_flag")
    lines.append(f"Cotes O/U : {_yes_no(odds_available)}")
    return lines


def _xg_str(prediction: Any) -> str:
    home = _number(getattr(prediction, "xg_home", None))
    away = _number(getattr(prediction, "xg_away", None))
    total = _number(getattr(prediction, "xg_total", None))
    if home is None or away is None:
        return _NA
    total_label = f"{total:.2f}" if total is not None else _NA
    return f"{home:.2f} + {away:.2f} = {total_label}"


def _date_str(dt: datetime | None, timezone_name: str) -> str:
    if dt is None:
        return _NA
    try:
        local = ensure_aware_utc(dt).astimezone(ZoneInfo(timezone_name))
        return f"{local.strftime('%d/%m/%Y')} · {local.strftime('%H:%M')} {timezone_name}"
    except Exception:
        return _clean(dt)


def _match_label(prediction: Any, fixture: Any | None) -> str:
    label = getattr(prediction, "match_label", None)
    if label:
        return _clean(label)
    if fixture is not None:
        home = getattr(fixture, "home_team_name", None) or getattr(fixture, "home_team", None)
        away = getattr(fixture, "away_team_name", None) or getattr(fixture, "away_team", None)
        if home and away:
            return f"{_clean(home)} vs {_clean(away)}"
    return f"Fixture #{_clean(getattr(prediction, 'fixture_id', '?'))}"


def _competition_label(prediction: Any, fixture: Any | None) -> str:
    comp = getattr(prediction, "competition", None)
    if comp:
        return _clean(comp)
    if fixture is not None:
        league = getattr(fixture, "league_name", None) or getattr(fixture, "competition", None)
        if league:
            return _clean(league)
    return _NA


def _kickoff_time(prediction: Any, fixture: Any | None) -> datetime | None:
    kickoff = getattr(prediction, "kickoff_time", None)
    if kickoff is not None:
        return kickoff
    if fixture is not None:
        return getattr(fixture, "date", None)
    return None


def _confidence_label(prediction: Any) -> str:
    value = getattr(prediction, "confidence_label_v2", None) or getattr(
        prediction, "confidence_label", _NA
    )
    return _clean(value).upper().replace("_", " ")


def _score_label(prediction: Any) -> str:
    value = _number(
        getattr(prediction, "confidence_score_v2", None),
        default=_number(getattr(prediction, "confidence_score", None)),
    )
    return f"{value:.0f}/100" if value is not None else _NA


def _pct(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.1f}%"


def _delta_str(value: float | None) -> str:
    if value is None:
        return _NA
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f} pts"


def _ev_str(value: float | None) -> str:
    if value is None:
        return _NA
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}%"


def _odd_str(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:.2f}"


def _quality_score_str(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:.0f}/100"


def _data_quality_score(payload: Any) -> float | None:
    if not isinstance(payload, Mapping):
        return None
    for key in (
        "ou_data_quality_score",
        "overall_data_quality_score",
        "publication_data_quality_score",
        "data_quality_score",
    ):
        value = _number(payload.get(key))
        if value is not None:
            return value
    return None


def _reason_label(reason: Any) -> str:
    labels = {
        "market_unavailable": "marché indisponible",
        "edge_below_threshold": "edge insuffisant",
        "edge_insufficient": "edge insuffisant",
        "ev_below_threshold": "EV insuffisante",
        "ev_insufficient": "EV insuffisante",
        "invalid_odds": "cotes invalides",
        "confidence_insufficient": "confiance insuffisante",
        "data_quality_insufficient": "data quality insuffisante",
        "bookmaker_count_insufficient": "nombre de bookmakers insuffisant",
        "no_value_side": "aucun côté value",
    }
    key = str(reason or "").strip()
    return labels.get(key, _clean(key) if key else _NA)


def _yes_no(value: Any) -> str:
    if value is None:
        return _NA
    return "oui" if bool(value) else "non"


def _side(value: Any, *, fallback: str | None) -> str | None:
    normalized = str(value or "").strip().upper()
    if normalized in {"OVER", "PLUS", "PLUS 2.5", "OVER 2.5"}:
        return "OVER"
    if normalized in {"UNDER", "MOINS", "MOINS 2.5", "UNDER 2.5"}:
        return "UNDER"
    return fallback


def _side_label(side: str | None) -> str:
    if side == "OVER":
        return "Plus de 2.5 buts"
    if side == "UNDER":
        return "Moins de 2.5 buts"
    return "No bet"


def _number(value: Any, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    text = str(value).replace("```", "'''").replace("\r", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[secret masqué]", text)
    return " ".join(text.split()) or _NA


def _truncate(message: str, limit: int) -> str:
    if len(message) <= limit:
        return message
    budget = limit - len(CODE_CLOSE) - len(_TRUNCATION) - 2
    truncated: list[str] = []
    used = 0
    for line in message.splitlines()[:-1]:
        if used + len(line) + 1 > budget:
            truncated.append(_TRUNCATION)
            break
        truncated.append(line)
        used += len(line) + 1
    truncated.append(CODE_CLOSE)
    return "\n".join(truncated)
