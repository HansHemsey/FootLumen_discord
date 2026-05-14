"""Discord formatters for match analyses and post-match results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from football_predictor.db import models
from football_predictor.discord.formatter import CODE_CLOSE, CODE_OPEN, truncate_discord_message
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.utils.secrets import sanitize_secret_text
from football_predictor.utils.time import format_in_timezone

DISCORD_SAFE_LIMIT = 1900

_UNAVAILABLE = "non disponible"
_OUTCOME_LABELS_FR = {
    "HOME": "victoire domicile",
    "DRAW": "match nul",
    "AWAY": "victoire extérieur",
}


def format_match_analysis_message(
    *,
    fixture: models.Fixture,
    prediction: models.ModelPrediction,
    features: Mapping[str, Any] | None = None,
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> str:
    """Render one concise H-6 analysis message for a fixture."""
    payload = prediction.payload_json if isinstance(prediction.payload_json, dict) else {}
    feature_payload = features or {}
    quality_payload = (
        prediction.data_quality_json if isinstance(prediction.data_quality_json, dict) else {}
    )
    probabilities = ProbabilityTriple(
        p_home=prediction.p_home,
        p_draw=prediction.p_draw,
        p_away=prediction.p_away,
    ).normalized()
    lines = [
        CODE_OPEN,
        "🧠 ANALYSE AVANT-MATCH H-6",
        "",
        f"Match : {_clean(fixture.home_team)} vs {_clean(fixture.away_team)}",
        f"Compétition : {_competition_label(fixture, payload)}",
        f"Date : {_datetime_label(fixture.date, timezone_name)}",
        f"Contexte : {_round_label(fixture)}",
        "",
        "Forme récente :",
        _form_line("Domicile", "home_team", feature_payload),
        _form_line("Extérieur", "away_team", feature_payload),
        "",
        "Classement / dynamique :",
        _standings_line(feature_payload),
        "",
        "Marché :",
        _market_line(feature_payload),
        _movement_line(feature_payload),
        "",
        "Absences / XI :",
        _absence_line("Domicile", "home_team_key_absences_json", feature_payload),
        _absence_line("Extérieur", "away_team_key_absences_json", feature_payload),
        _xi_line(feature_payload),
        "",
        "Points forts / faibles :",
        *_analysis_edges(feature_payload),
        "",
        "Probabilités pré-match :",
        f"- Domicile : {_percent(probabilities.p_home)}",
        f"- Nul      : {_percent(probabilities.p_draw)}",
        f"- Extérieur: {_percent(probabilities.p_away)}",
        f"Confiance : {prediction.confidence_label} ({prediction.confidence_score:.1f} pts)",
        "",
        "Fiabilité des données :",
        _quality_line(quality_payload),
        "",
        "Conclusion : lecture prudente, probabiliste, à ne pas considérer comme une certitude.",
        CODE_CLOSE,
    ]
    return truncate_discord_message("\n".join(lines), max_chars=max_chars)


def format_match_result_message(
    *,
    fixture: models.Fixture,
    prediction: models.ModelPrediction | None = None,
    timezone_name: str = "Europe/Paris",
    max_chars: int = DISCORD_SAFE_LIMIT,
) -> str:
    """Render one concise post-match result message, with prediction comparison if available."""
    payload = (
        prediction.payload_json
        if prediction is not None and isinstance(prediction.payload_json, dict)
        else {}
    )
    home_goals = _goals_home(fixture)
    away_goals = _goals_away(fixture)
    actual = _actual_outcome(home_goals, away_goals)
    predicted = prediction.predicted_result if prediction is not None else None
    correct = actual is not None and predicted is not None and actual == predicted
    lines = [
        CODE_OPEN,
        "✅ RÉSULTAT MATCH",
        "",
        f"Match : {_clean(fixture.home_team)} vs {_clean(fixture.away_team)}",
        f"Compétition : {_competition_label(fixture, payload)}",
        f"Date : {_datetime_label(fixture.date, timezone_name)}",
        f"Score final : {_score_label(home_goals, away_goals)}",
        f"Résultat 1X2 : {_outcome_label(actual)}",
        "",
        "Prédiction publiée :",
        f"- Choix : {_outcome_label(predicted)}",
        *_prediction_probability_lines(prediction),
        f"- Confiance initiale : {_confidence_label(prediction)}",
        "",
        f"Pronostic : {_forecast_label(correct, actual, predicted)}",
        f"Mini bilan : {_result_summary(actual, predicted, correct)}",
        CODE_CLOSE,
    ]
    return truncate_discord_message("\n".join(lines), max_chars=max_chars)


def _competition_label(fixture: models.Fixture, payload: Mapping[str, Any]) -> str:
    value = payload.get("competition")
    if value:
        return _clean(value)
    return f"League {fixture.league_id} - {fixture.season}"


def _datetime_label(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return _UNAVAILABLE
    return f"{format_in_timezone(value, timezone_name)} {timezone_name}"


def _round_label(fixture: models.Fixture) -> str:
    parts = [part for part in (fixture.round, fixture.venue_name, fixture.status_short) if part]
    return " | ".join(_clean(part) for part in parts) if parts else _UNAVAILABLE


def _form_line(label: str, prefix: str, features: Mapping[str, Any]) -> str:
    ppg = _number(features.get(f"{prefix}_global_last5_ppg"))
    gd = _number(features.get(f"{prefix}_global_goal_diff_avg_last5"))
    xg = _number(features.get(f"{prefix}_global_pseudo_xg_avg_last5"))
    return f"- {label} : PPG {_fmt(ppg)}, diff {_fmt(gd)}, pseudo-xG {_fmt(xg)}"


def _standings_line(features: Mapping[str, Any]) -> str:
    rank_diff = _number(features.get("rank_diff"))
    points_diff = _number(features.get("points_diff"))
    goals_diff = _number(features.get("goals_diff_diff"))
    if rank_diff is None and points_diff is None and goals_diff is None:
        return "- non disponible"
    return (
        f"- Écart rang {_fmt(rank_diff)}, points {_fmt(points_diff)}, "
        f"diff buts {_fmt(goals_diff)}"
    )


def _market_line(features: Mapping[str, Any]) -> str:
    home = _number(features.get("market_home") or features.get("p_market_home"))
    draw = _number(features.get("market_draw") or features.get("p_market_draw"))
    away = _number(features.get("market_away") or features.get("p_market_away"))
    count = features.get("market_bookmaker_count")
    if home is None or draw is None or away is None:
        return "- probabilités marché non disponibles"
    return (
        f"- Domicile {_percent(home)}, Nul {_percent(draw)}, Extérieur {_percent(away)} "
        f"({count or 0} bookmaker(s))"
    )


def _movement_line(features: Mapping[str, Any]) -> str:
    home = _number(features.get("odds_movement_home"))
    draw = _number(features.get("odds_movement_draw"))
    away = _number(features.get("odds_movement_away"))
    if home is None and draw is None and away is None:
        return "- mouvement de cotes non disponible"
    return f"- mouvement odds H {_fmt(home)}, N {_fmt(draw)}, A {_fmt(away)}"


def _absence_line(label: str, key: str, features: Mapping[str, Any]) -> str:
    absences = features.get(key)
    if not isinstance(absences, Sequence) or isinstance(absences, str | bytes) or not absences:
        return f"- {label} : non disponible"
    rendered: list[str] = []
    for item in absences[:2]:
        if isinstance(item, Mapping):
            name = item.get("name") or item.get("player_name") or item.get("player")
            reason = item.get("reason") or item.get("type") or item.get("status")
            if name:
                rendered.append(f"{_clean(name)} ({_clean(reason or 'raison n.d.')})")
    return f"- {label} : " + ("; ".join(rendered) if rendered else "non disponible")


def _xi_line(features: Mapping[str, Any]) -> str:
    home_form = features.get("home_team_probable_formation") or features.get(
        "home_team_formation_probable"
    )
    away_form = features.get("away_team_probable_formation") or features.get(
        "away_team_formation_probable"
    )
    home_stability = _number(features.get("home_team_xi_stability_score"))
    away_stability = _number(features.get("away_team_xi_stability_score"))
    if not any((home_form, away_form, home_stability, away_stability)):
        return "- XI probable : non disponible"
    return (
        f"- XI : {_clean(home_form or 'n.d.')} vs {_clean(away_form or 'n.d.')}, "
        f"stabilité {_fmt(home_stability)} / {_fmt(away_stability)}"
    )


def _analysis_edges(features: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    rows.append(
        _edge_line(
            "Forme",
            features.get("home_team_global_last5_ppg"),
            features.get("away_team_global_last5_ppg"),
        )
    )
    rows.append(
        _edge_line(
            "Pseudo-xG",
            features.get("home_team_global_pseudo_xg_avg_last5"),
            features.get("away_team_global_pseudo_xg_avg_last5"),
        )
    )
    rows.append(
        _edge_line(
            "Disponibilité",
            features.get("home_team_availability_score"),
            features.get("away_team_availability_score"),
        )
    )
    return [row for row in rows if row] or ["- non disponible"]


def _edge_line(label: str, home_raw: Any, away_raw: Any) -> str:
    home = _number(home_raw)
    away = _number(away_raw)
    if home is None or away is None:
        return f"- {label} : non disponible"
    diff = home - away
    side = "domicile" if diff > 0 else "extérieur" if diff < 0 else "équilibre"
    return f"- {label} : avantage {side} ({_fmt(diff)})"


def _quality_line(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return "- Score global : non disponible"
    score = payload.get("overall_data_quality_score")
    odds = _yes_no(payload.get("odds_available_flag"))
    target_lineups = _yes_no(payload.get("target_lineups_available_flag"))
    historical_lineups = _yes_no(
        payload.get("historical_lineups_available_flag", payload.get("lineups_available_flag"))
    )
    players = _yes_no(
        (
            payload.get(
                "historical_player_stats_available_rate",
                payload.get("player_stats_available_rate") or 0,
            )
            or 0
        )
        > 0
    )
    return (
        f"- Score global : {_fmt(_number(score), digits=0)}/100 | "
        f"Odds {odds} | Lineups cible {target_lineups} | "
        f"Hist. lineups {historical_lineups} | Joueurs hist. {players}"
    )


def _prediction_probability_lines(prediction: models.ModelPrediction | None) -> list[str]:
    if prediction is None:
        return [
            "- Domicile : non disponible",
            "- Nul      : non disponible",
            "- Extérieur: non disponible",
        ]
    probabilities = ProbabilityTriple(
        p_home=prediction.p_home,
        p_draw=prediction.p_draw,
        p_away=prediction.p_away,
    ).normalized()
    return [
        f"- Domicile : {_percent(probabilities.p_home)}",
        f"- Nul      : {_percent(probabilities.p_draw)}",
        f"- Extérieur: {_percent(probabilities.p_away)}",
    ]


def _confidence_label(prediction: models.ModelPrediction | None) -> str:
    if prediction is None:
        return _UNAVAILABLE
    return f"{prediction.confidence_label} ({prediction.confidence_score:.1f} pts)"


def _forecast_label(correct: bool, actual: str | None, predicted: str | None) -> str:
    if actual is None:
        return "résultat final non disponible"
    if predicted is None:
        return "aucune prédiction pré-match retrouvée"
    return "correct" if correct else "incorrect"


def _result_summary(actual: str | None, predicted: str | None, correct: bool) -> str:
    if actual is None:
        return "score final absent, bilan impossible."
    if predicted is None:
        return "résultat publié sans comparaison faute de prédiction pré-match."
    if correct:
        return "la tendance pré-match a été confirmée."
    return "la tendance pré-match n'a pas été confirmée."


def _actual_outcome(home_goals: int | None, away_goals: int | None) -> str | None:
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "HOME"
    if home_goals < away_goals:
        return "AWAY"
    return "DRAW"


def _outcome_label(value: str | None) -> str:
    if value is None:
        return _UNAVAILABLE
    return _OUTCOME_LABELS_FR.get(value.upper(), value)


def _score_label(home_goals: int | None, away_goals: int | None) -> str:
    if home_goals is None or away_goals is None:
        return _UNAVAILABLE
    return f"{home_goals}-{away_goals}"


def _goals_home(fixture: models.Fixture) -> int | None:
    return fixture.home_goals if fixture.home_goals is not None else fixture.goals_home


def _goals_away(fixture: models.Fixture) -> int | None:
    return fixture.away_goals if fixture.away_goals is not None else fixture.goals_away


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "n.d."
    return f"{value:.{digits}f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "non disponible"
    return f"{value * 100:.1f}%"


def _yes_no(value: Any) -> str:
    return "oui" if bool(value) else "non"


def _clean(value: object) -> str:
    text = str(value).replace("```", "'''").replace("\r", " ").replace("\n", " ").strip()
    text = sanitize_secret_text(text, replacement="[secret masqué]")
    return " ".join(text.split()) or _UNAVAILABLE
