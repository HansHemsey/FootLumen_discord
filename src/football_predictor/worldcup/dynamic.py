"""Point-in-time dynamic features for World Cup predictions."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.features.lineup_m30_features import build_lineup_m30_features
from football_predictor.features.odds_features import (
    compute_market_consensus,
    compute_odds_movement,
)
from football_predictor.features.xi_features import build_player_xi_features
from football_predictor.modeling.probabilities import ProbabilityTriple
from football_predictor.reference.lookups import PlayersReference
from football_predictor.utils.time import ensure_aware_utc
from football_predictor.worldcup.features import poisson_probabilities, probability_from_rating_diff

JsonDict = dict[str, Any]


def build_worldcup_dynamic_features(
    session: Session,
    fixture: models.Fixture,
    prediction_time: datetime,
    *,
    players_reference: PlayersReference | None = None,
) -> JsonDict:
    """Build DB-backed M-30 features without reading after prediction_time."""
    cutoff = ensure_aware_utc(prediction_time)
    features: JsonDict = {}
    features.update(_market_features(session, fixture.fixture_id, cutoff))
    features.update(_api_prediction_features(session, fixture, cutoff))
    features.update(_lineup_features(session, fixture.fixture_id, cutoff))
    features.update(_absence_features(session, fixture.fixture_id, cutoff, players_reference))
    features.update(_dynamic_source_flags(features))
    return features


def apply_dynamic_probability_features(features: JsonDict) -> JsonDict:
    """Derive dynamic rating and Poisson probabilities from lineups/injuries."""
    home_penalty = _team_penalty(features, "home")
    away_penalty = _team_penalty(features, "away")
    base_margin = _numeric(features.get("wc_expected_margin"), 0.0)
    dynamic_margin = base_margin + away_penalty - home_penalty
    base_home_goals = _numeric(features.get("wc_expected_home_goals"), 1.35)
    base_away_goals = _numeric(features.get("wc_expected_away_goals"), 1.10)
    dynamic_home_goals = _bounded(base_home_goals - home_penalty + away_penalty * 0.5, 0.2, 4.5)
    dynamic_away_goals = _bounded(base_away_goals - away_penalty + home_penalty * 0.5, 0.2, 4.5)
    rating = probability_from_rating_diff(dynamic_margin * 400.0)
    poisson = poisson_probabilities(dynamic_home_goals, dynamic_away_goals)
    return {
        "wc_home_dynamic_penalty": home_penalty,
        "wc_away_dynamic_penalty": away_penalty,
        "wc_dynamic_penalty_diff": home_penalty - away_penalty,
        "wc_expected_margin_dynamic": dynamic_margin,
        "wc_expected_home_goals_dynamic": dynamic_home_goals,
        "wc_expected_away_goals_dynamic": dynamic_away_goals,
        "wc_total_expected_goals_dynamic": dynamic_home_goals + dynamic_away_goals,
        "p_wc_rating_dynamic_home": rating.p_home,
        "p_wc_rating_dynamic_draw": rating.p_draw,
        "p_wc_rating_dynamic_away": rating.p_away,
        "p_wc_poisson_dynamic_home": poisson.p_home,
        "p_wc_poisson_dynamic_draw": poisson.p_draw,
        "p_wc_poisson_dynamic_away": poisson.p_away,
    }


def _market_features(session: Session, fixture_id: int, cutoff: datetime) -> JsonDict:
    market = compute_market_consensus(session, fixture_id, cutoff)
    movement = compute_odds_movement(session, fixture_id, cutoff)
    if market is None:
        return {
            "wc_market_available_flag": 0,
            "p_wc_market_home": None,
            "p_wc_market_draw": None,
            "p_wc_market_away": None,
            "wc_market_bookmaker_count": 0,
            "wc_market_overround": None,
            "wc_market_dispersion": None,
            "wc_market_confidence": None,
            "wc_market_fetched_at": None,
            "wc_market_movement_home": movement.delta_home,
            "wc_market_movement_draw": movement.delta_draw,
            "wc_market_movement_away": movement.delta_away,
        }
    return {
        "wc_market_available_flag": 1,
        "p_wc_market_home": market.p_market_home,
        "p_wc_market_draw": market.p_market_draw,
        "p_wc_market_away": market.p_market_away,
        "wc_market_bookmaker_count": market.bookmaker_count,
        "wc_market_overround": market.overround,
        "wc_market_dispersion": market.market_dispersion,
        "wc_market_confidence": market.market_confidence,
        "wc_market_fetched_at": ensure_aware_utc(market.fetched_at).isoformat(),
        "wc_market_movement_home": movement.delta_home,
        "wc_market_movement_draw": movement.delta_draw,
        "wc_market_movement_away": movement.delta_away,
    }


def _api_prediction_features(
    session: Session,
    fixture: models.Fixture,
    cutoff: datetime,
) -> JsonDict:
    snapshot = session.execute(
        select(models.ApiPredictionSnapshot)
        .where(
            models.ApiPredictionSnapshot.fixture_id == fixture.fixture_id,
            models.ApiPredictionSnapshot.fetched_at <= cutoff,
        )
        .order_by(models.ApiPredictionSnapshot.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if snapshot is None:
        return {
            "wc_api_pred_available_flag": 0,
            "p_wc_api_home": None,
            "p_wc_api_draw": None,
            "p_wc_api_away": None,
            "wc_api_pred_winner_home_flag": 0,
            "wc_api_pred_winner_away_flag": 0,
            "wc_api_pred_win_or_draw_flag": 0,
            "wc_api_pred_fetched_at": None,
        }
    home = _normalize_percent(snapshot.percent_home)
    draw = _normalize_percent(snapshot.percent_draw)
    away = _normalize_percent(snapshot.percent_away)
    probability = _probability_or_none(home, draw, away)
    return {
        "wc_api_pred_available_flag": int(probability is not None),
        "p_wc_api_home": probability.p_home if probability else None,
        "p_wc_api_draw": probability.p_draw if probability else None,
        "p_wc_api_away": probability.p_away if probability else None,
        "wc_api_pred_winner_home_flag": int(snapshot.winner_team_id == fixture.home_team_id),
        "wc_api_pred_winner_away_flag": int(snapshot.winner_team_id == fixture.away_team_id),
        "wc_api_pred_win_or_draw_flag": int(bool(snapshot.win_or_draw)),
        "wc_api_pred_fetched_at": ensure_aware_utc(snapshot.fetched_at).isoformat(),
    }


def _lineup_features(session: Session, fixture_id: int, cutoff: datetime) -> JsonDict:
    lineup = build_lineup_m30_features(session, fixture_id, cutoff)
    return {
        **lineup,
        "wc_official_lineup_available_flag": int(lineup.get("official_lineup_available_flag") or 0),
        "wc_official_lineup_home_available_flag": int(
            lineup.get("official_lineup_home_available_flag") or 0
        ),
        "wc_official_lineup_away_available_flag": int(
            lineup.get("official_lineup_away_available_flag") or 0
        ),
        "wc_home_formation_change_flag": int(
            lineup.get("home_team_formation_change_flag") or 0
        ),
        "wc_away_formation_change_flag": int(
            lineup.get("away_team_formation_change_flag") or 0
        ),
        "wc_home_lineup_surprise_score": lineup.get("home_team_lineup_surprise_score"),
        "wc_away_lineup_surprise_score": lineup.get("away_team_lineup_surprise_score"),
        "wc_home_formation_stability_score": lineup.get("home_team_formation_stability_score"),
        "wc_away_formation_stability_score": lineup.get("away_team_formation_stability_score"),
    }


def _absence_features(
    session: Session,
    fixture_id: int,
    cutoff: datetime,
    players_reference: PlayersReference | None,
) -> JsonDict:
    try:
        xi = build_player_xi_features(
            session,
            fixture_id,
            cutoff,
            players_reference=players_reference,
        )
    except Exception as exc:
        return {
            "wc_home_absence_impact_score": 0.0,
            "wc_away_absence_impact_score": 0.0,
            "wc_home_availability_score": 1.0,
            "wc_away_availability_score": 1.0,
            "wc_home_starter_missing_count": 0,
            "wc_away_starter_missing_count": 0,
            "wc_home_key_absences_count": 0,
            "wc_away_key_absences_count": 0,
            "wc_injuries_available_flag": 0,
            "wc_dynamic_warning": f"xi_features_unavailable: {exc}",
        }
    features = xi.features_json
    quality = xi.data_quality_json
    home_absences = features.get("home_team_key_absences_json")
    away_absences = features.get("away_team_key_absences_json")
    return {
        "wc_home_absence_impact_score": _numeric(
            features.get("home_team_absence_impact_score"), 0.0
        ),
        "wc_away_absence_impact_score": _numeric(
            features.get("away_team_absence_impact_score"), 0.0
        ),
        "wc_home_availability_score": _numeric(features.get("home_team_availability_score"), 1.0),
        "wc_away_availability_score": _numeric(features.get("away_team_availability_score"), 1.0),
        "wc_home_replacement_quality_score": _numeric(
            features.get("home_team_replacement_quality_score"), 1.0
        ),
        "wc_away_replacement_quality_score": _numeric(
            features.get("away_team_replacement_quality_score"), 1.0
        ),
        "wc_home_starter_missing_count": int(features.get("home_team_starter_missing_count") or 0),
        "wc_away_starter_missing_count": int(features.get("away_team_starter_missing_count") or 0),
        "wc_home_key_absences_count": len(home_absences) if isinstance(home_absences, list) else 0,
        "wc_away_key_absences_count": len(away_absences) if isinstance(away_absences, list) else 0,
        "wc_injuries_available_flag": int(
            int(quality.get("home_team_injuries_available") or 0) > 0
            or int(quality.get("away_team_injuries_available") or 0) > 0
        ),
        "wc_home_key_absences_json": home_absences if isinstance(home_absences, list) else [],
        "wc_away_key_absences_json": away_absences if isinstance(away_absences, list) else [],
    }


def _dynamic_source_flags(features: JsonDict) -> JsonDict:
    source_flags = {
        "market": int(features.get("wc_market_available_flag") or 0),
        "api_prediction": int(features.get("wc_api_pred_available_flag") or 0),
        "lineups": int(features.get("wc_official_lineup_available_flag") or 0),
        "injuries": int(features.get("wc_injuries_available_flag") or 0),
    }
    return {
        "wc_dynamic_market_available_flag": source_flags["market"],
        "wc_dynamic_api_prediction_available_flag": source_flags["api_prediction"],
        "wc_dynamic_lineups_available_flag": source_flags["lineups"],
        "wc_dynamic_injuries_available_flag": source_flags["injuries"],
        "wc_dynamic_source_count": sum(source_flags.values()),
        "wc_dynamic_any_source_available_flag": int(any(source_flags.values())),
    }


def _team_penalty(features: JsonDict, side: str) -> float:
    absence = _bounded(_numeric(features.get(f"wc_{side}_absence_impact_score"), 0.0), 0.0, 1.0)
    surprise = _bounded(_numeric(features.get(f"wc_{side}_lineup_surprise_score"), 0.0), 0.0, 1.0)
    formation_change = 1.0 if int(features.get(f"wc_{side}_formation_change_flag") or 0) else 0.0
    return _bounded(0.12 * absence + 0.05 * surprise + 0.03 * formation_change, 0.0, 0.25)


def _probability_or_none(
    home: float | None,
    draw: float | None,
    away: float | None,
) -> ProbabilityTriple | None:
    if home is None or draw is None or away is None:
        return None
    total = home + draw + away
    if total <= 0:
        return None
    return ProbabilityTriple(home / total, draw / total, away / total).normalized()


def _normalize_percent(value: float | None) -> float | None:
    if value is None:
        return None
    parsed = _numeric(value)
    if parsed is None:
        return None
    return parsed / 100.0 if parsed > 1 else parsed


def _numeric(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _bounded(value: float | None, lower: float, upper: float) -> float:
    if value is None or not math.isfinite(value):
        return (lower + upper) / 2.0
    return min(max(value, lower), upper)
