"""Human-readable prediction explanations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.prediction.confidence import confidence_gap

JsonDict = dict[str, Any]


def explain_prediction(
    *,
    features: Mapping[str, Any],
    probabilities: ProbabilityTriple,
    data_quality: Mapping[str, Any] | None = None,
    sources_used: Sequence[str] = (),
    sport_source: str | None = None,
    home_team_name: str = "domicile",
    away_team_name: str = "exterieur",
    max_items: int = 5,
) -> list[str]:
    """Return short French factors without inventing unavailable data."""
    explanations = [
        _source_summary(sources_used, sport_source),
        _market_favorite(features, home_team_name, away_team_name),
        _team_form_edge(features, home_team_name, away_team_name),
        _home_away_edge(features, home_team_name, away_team_name),
        _absence_edge(features, home_team_name, away_team_name),
        _xi_stability_edge(features, home_team_name, away_team_name),
        _standings_edge(features, home_team_name, away_team_name),
        _pseudo_xg_edge(features, home_team_name, away_team_name),
        _odds_movement(features),
        _probability_edge(probabilities),
        _quality_warning(data_quality or {}),
    ]
    return [item for item in explanations if item][:max_items]


def _source_summary(sources_used: Sequence[str], sport_source: str | None) -> str:
    if not sources_used:
        return "Aucune source dynamique complete : fallback conservateur utilise."
    sport = f" via {sport_source}" if sport_source else ""
    return f"Sources combinees : {', '.join(sources_used)}{sport}."


def _market_favorite(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    market = _triple_from_keys(features, ("market_home", "market_draw", "market_away"))
    if market is None:
        return "Marche 1X2 indisponible avant prediction_time."
    label = _label_for_result(market.predicted_result(), home_team_name, away_team_name)
    return f"Le marche 1X2 donne l'avantage a {label} ({market.max_probability() * 100:.1f}%)."


def _team_form_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    home = _first_numeric(
        features,
        ("home_team_global_last5_ppg", "home_team_global_points_per_match_last5"),
    )
    away = _first_numeric(
        features,
        ("away_team_global_last5_ppg", "away_team_global_points_per_match_last5"),
    )
    if home is None or away is None:
        return "Forme recente equipe indisponible ou incomplete."
    return _edge_sentence("forme recente", home, away, home_team_name, away_team_name, "PPM")


def _home_away_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    home = _first_numeric(
        features,
        ("home_team_home_last5_ppg", "home_team_home_points_per_match_last5"),
    )
    away = _first_numeric(
        features,
        ("away_team_away_last5_ppg", "away_team_away_points_per_match_last5"),
    )
    if home is None or away is None:
        return "Split domicile/exterieur indisponible ou incomplet."
    return _edge_sentence("domicile/exterieur", home, away, home_team_name, away_team_name, "PPM")


def _absence_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    home = _numeric(features.get("home_team_absence_impact_score"))
    away = _numeric(features.get("away_team_absence_impact_score"))
    if home is None and away is None:
        return "Absences non disponibles avant prediction_time."
    return _lower_is_better_sentence(
        "impact absences",
        home or 0.0,
        away or 0.0,
        home_team_name,
        away_team_name,
    )


def _xi_stability_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    home = _numeric(features.get("home_team_xi_stability_score"))
    away = _numeric(features.get("away_team_xi_stability_score"))
    if home is None or away is None:
        return "Stabilite du XI indisponible."
    return _edge_sentence("stabilite du XI", home, away, home_team_name, away_team_name, "score")


def _standings_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    rank_diff = _numeric(features.get("rank_diff"))
    points_diff = _numeric(features.get("points_diff"))
    if rank_diff is None and points_diff is None:
        return "Classement indisponible avant prediction_time."
    if points_diff is not None and abs(points_diff) >= 1:
        leader = home_team_name if points_diff > 0 else away_team_name
        return f"Avantage classement aux points pour {leader} ({points_diff:+.1f})."
    leader = home_team_name if (rank_diff or 0.0) < 0 else away_team_name
    return f"Avantage classement au rang pour {leader}."


def _pseudo_xg_edge(
    features: Mapping[str, Any],
    home_team_name: str,
    away_team_name: str,
) -> str:
    home = _first_numeric(
        features,
        ("home_team_global_pseudo_xg_avg_last5", "home_team_global_pseudo_xg_avg_last3"),
    )
    away = _first_numeric(
        features,
        ("away_team_global_pseudo_xg_avg_last5", "away_team_global_pseudo_xg_avg_last3"),
    )
    if home is None or away is None:
        return "Pseudo-xG indisponible avec les stats actuelles."
    return _edge_sentence("pseudo-xG", home, away, home_team_name, away_team_name, "xG")


def _odds_movement(features: Mapping[str, Any]) -> str:
    home = _numeric(features.get("odds_movement_home"))
    draw = _numeric(features.get("odds_movement_draw"))
    away = _numeric(features.get("odds_movement_away"))
    if home is None and draw is None and away is None:
        return "Mouvement des cotes indisponible."
    return (
        "Mouvement des cotes observe avant prediction_time "
        f"(H {home or 0:+.2f}, N {draw or 0:+.2f}, A {away or 0:+.2f})."
    )


def _probability_edge(probabilities: ProbabilityTriple) -> str:
    gap = confidence_gap(probabilities) * 100
    return f"Ecart de probabilite entre les deux premiers choix : {gap:.1f} pts."


def _quality_warning(data_quality: Mapping[str, Any]) -> str:
    score = _numeric(data_quality.get("overall_data_quality_score"))
    if score is None:
        return "Qualite des donnees non calculee."
    if score < 50:
        return f"Qualite des donnees faible ({score:.0f}/100), prudence renforcee."
    return f"Qualite des donnees : {score:.0f}/100."


def _triple_from_keys(
    features: Mapping[str, Any],
    keys: tuple[str, str, str],
) -> ProbabilityTriple | None:
    values: list[float] = []
    for key in keys:
        value = _numeric(features.get(key))
        if value is None:
            return None
        values.append(value)
    try:
        return ProbabilityTriple.from_vector(values)
    except ValueError:
        return None


def _first_numeric(features: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        value = _numeric(features.get(key))
        if value is not None:
            return value
    return None


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _edge_sentence(
    label: str,
    home: float,
    away: float,
    home_team_name: str,
    away_team_name: str,
    unit: str,
) -> str:
    leader = home_team_name if home >= away else away_team_name
    return f"Avantage {label} pour {leader} ({home:.2f} vs {away:.2f} {unit})."


def _lower_is_better_sentence(
    label: str,
    home: float,
    away: float,
    home_team_name: str,
    away_team_name: str,
) -> str:
    leader = home_team_name if home <= away else away_team_name
    return f"Avantage {label} pour {leader} ({home:.2f} vs {away:.2f})."


def _label_for_result(result: str, home_team_name: str, away_team_name: str) -> str:
    if result == "HOME":
        return home_team_name
    if result == "AWAY":
        return away_team_name
    return "match nul"
