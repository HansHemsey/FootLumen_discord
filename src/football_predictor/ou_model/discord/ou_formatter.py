"""Discord markdown formatter for O/U 2.5 predictions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from football_predictor.utils.time import format_in_timezone

DISCORD_LIMIT = 1900
CODE_OPEN = "```md"
CODE_CLOSE = "```"
_TRUNCATION = "... message tronqué ..."
_NA = "N/A"


def _pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.{decimals}f}%"


def _odd(value: float | None) -> str:
    if value is None:
        return _NA
    return f"{value:.2f}"


def _edge_str(value: float | None) -> str:
    if value is None:
        return _NA
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}%"


def _xg_str(home: float | None, away: float | None, total: float | None) -> str:
    if home is None or away is None:
        return _NA
    total_str = f"{total:.2f}" if total is not None else _NA
    return f"{home:.2f} + {away:.2f} = {total_str}"


def _date_str(dt: datetime | None, timezone_name: str) -> str:
    if dt is None:
        return _NA
    try:
        from zoneinfo import ZoneInfo
        from football_predictor.utils.time import ensure_aware_utc
        local = ensure_aware_utc(dt).astimezone(ZoneInfo(timezone_name))
        return local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


def _match_label(prediction: Any, fixture: Any | None) -> str:
    # Prefer pre-resolved label from the prediction object
    label = getattr(prediction, "match_label", None)
    if label:
        return label
    # Fall back to fixture ORM relations if available
    if fixture is not None:
        home = getattr(fixture, "home_team_name", None) or getattr(fixture, "home_team", None)
        away = getattr(fixture, "away_team_name", None) or getattr(fixture, "away_team", None)
        if home and away:
            return f"{home} vs {away}"
    return f"Fixture #{getattr(prediction, 'fixture_id', '?')}"


def _competition_label(prediction: Any, fixture: Any | None) -> str:
    # Prefer pre-resolved competition from the prediction object
    comp = getattr(prediction, "competition", None)
    if comp:
        return str(comp)
    if fixture is not None:
        league = getattr(fixture, "league_name", None) or getattr(fixture, "competition", None)
        if league:
            return str(league)
    return _NA


def _kickoff_time(prediction: Any, fixture: Any | None) -> datetime | None:
    # Prefer kickoff_time resolved at prediction time
    kt = getattr(prediction, "kickoff_time", None)
    if kt is not None:
        return kt
    # Fall back to fixture.date
    if fixture is not None:
        return getattr(fixture, "date", None)
    return None


def _experts_lines(experts: dict[str, float] | None) -> list[str]:
    if not experts:
        return []
    lines = ["Sources experts :"]
    for name, p in sorted(experts.items()):
        lines.append(f"  {name:<12} {_pct(p)}")
    return lines


def format_ou_prediction_markdown(
    prediction: Any,
    fixture: Any | None = None,
    *,
    timezone_name: str = "Europe/Paris",
    limit: int = DISCORD_LIMIT,
    edge_display_threshold: float = 0.02,
) -> str:
    """Format an OUPredictionOutput as a Discord-safe markdown code block."""
    p_over: float = getattr(prediction, "p_over", 0.5)
    p_under: float = getattr(prediction, "p_under", 0.5)
    predicted_side = "PLUS DE 2.5 BUTS" if p_over >= p_under else "MOINS DE 2.5 BUTS"

    xg_home = getattr(prediction, "xg_home", None)
    xg_away = getattr(prediction, "xg_away", None)
    xg_total = getattr(prediction, "xg_total", None)

    odd_over = getattr(prediction, "market_odd_over", None)
    odd_under = getattr(prediction, "market_odd_under", None)
    market_p_over = getattr(prediction, "market_p_over", None)
    market_p_under = getattr(prediction, "market_p_under", None)

    edge_over = getattr(prediction, "edge_over", None)
    edge_under = getattr(prediction, "edge_under", None)
    ev_over = getattr(prediction, "ev_over", None)
    ev_under = getattr(prediction, "ev_under", None)

    conf_label: str = getattr(prediction, "confidence_label", _NA)
    conf_score: float | None = getattr(prediction, "confidence_score", None)
    kickoff: datetime | None = _kickoff_time(prediction, fixture)
    experts: dict[str, float] | None = getattr(prediction, "expert_probabilities", None)

    show_edge_over = edge_over is not None and abs(edge_over) >= edge_display_threshold
    show_edge_under = edge_under is not None and abs(edge_under) >= edge_display_threshold

    lines: list[str] = [
        CODE_OPEN,
        "PRONOSTIC O/U 2.5 BUTS",
        "",
        f"Match        : {_match_label(prediction, fixture)}",
        f"Compétition  : {_competition_label(prediction, fixture)}",
        f"Coup d'envoi : {_date_str(kickoff, timezone_name)}",
        "",
        f"Résultat prédit : {predicted_side}",
        f"P(Plus de 2.5)  : {_pct(p_over)}",
        f"P(Moins de 2.5) : {_pct(p_under)}",
        "",
        f"xG prévu        : {_xg_str(xg_home, xg_away, xg_total)}",
        "",
    ]

    if odd_over is not None or odd_under is not None:
        lines += [
            "Cotes marché :",
            f"  Plus 2.5  : {_odd(odd_over)}  (impliqué {_pct(market_p_over)})",
            f"  Moins 2.5 : {_odd(odd_under)}  (impliqué {_pct(market_p_under)})",
            "",
        ]

    if show_edge_over:
        lines += [
            f"Edge PLUS   : {_edge_str(edge_over)}",
            f"EV PLUS     : {_edge_str(ev_over)} / unité",
            "",
        ]
    if show_edge_under:
        lines += [
            f"Edge MOINS  : {_edge_str(edge_under)}",
            f"EV MOINS    : {_edge_str(ev_under)} / unité",
            "",
        ]

    conf_str = f"{conf_label}"
    if conf_score is not None:
        conf_str += f" ({conf_score:.0f}/100)"
    lines.append(f"Confiance    : {conf_str}")
    lines.append("")

    if experts:
        lines += _experts_lines(experts)
        lines.append("")

    lines.append(CODE_CLOSE)

    raw = "\n".join(lines)
    if len(raw) <= limit:
        return raw

    truncated: list[str] = []
    budget = limit - len(CODE_CLOSE) - len(_TRUNCATION) - 2
    used = 0
    for line in lines[:-1]:
        if used + len(line) + 1 > budget:
            truncated.append(_TRUNCATION)
            break
        truncated.append(line)
        used += len(line) + 1
    truncated.append(CODE_CLOSE)
    return "\n".join(truncated)
