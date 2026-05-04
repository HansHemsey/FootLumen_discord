"""Global point-in-time feature snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.odds_features import (
    compute_market_consensus,
    compute_odds_movement,
    resolve_1x2_bet_id,
)
from football_predictor.features.team_features import build_team_features
from football_predictor.features.xi_features import build_player_xi_features
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import DataQualityError, ReferenceLookupError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class GlobalFeatureConfig:
    feature_version: str = "global_features_v1"
    prediction_windows: tuple[str, ...] = ("24h", "6h", "40m")
    market_bet_id: int | None = None


@dataclass(frozen=True)
class GlobalFeatureResult:
    features_json: JsonDict
    data_quality_json: JsonDict


def build_feature_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
    config: GlobalFeatureConfig | None = None,
) -> models.FeatureSnapshot:
    """Build and store a complete point-in-time feature snapshot."""
    resolved_config = config or GlobalFeatureConfig()
    result = build_global_features(
        session,
        fixture_id,
        prediction_time,
        players_reference=players_reference,
        api_reference=api_reference,
        config=resolved_config,
    )
    prediction_cutoff = ensure_aware_utc(prediction_time)
    snapshot = upsert_by_fields(
        session,
        models.FeatureSnapshot,
        {
            "fixture_id": fixture_id,
            "prediction_time": prediction_cutoff,
            "feature_version": resolved_config.feature_version,
        },
        {
            "features_json": result.features_json,
            "data_quality_json": result.data_quality_json,
        },
    )
    session.flush()
    return snapshot


def build_global_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
    config: GlobalFeatureConfig | None = None,
) -> GlobalFeatureResult:
    """Merge team, player/XI, market and API prediction features."""
    resolved_config = config or GlobalFeatureConfig()
    prediction_cutoff = ensure_aware_utc(prediction_time)
    session.flush()
    target = session.get(models.Fixture, fixture_id)
    if target is None:
        raise DataQualityError(f"Unknown fixture_id={fixture_id}")

    team_result = build_team_features(session, fixture_id, prediction_cutoff)
    xi_result = build_player_xi_features(
        session,
        fixture_id,
        prediction_cutoff,
        players_reference=players_reference,
    )
    bet_id = _resolve_market_bet_id(resolved_config, api_reference)
    market_features, market_quality = _market_features(
        session,
        fixture_id,
        prediction_cutoff,
        bet_id=bet_id,
    )
    api_features, api_quality = _api_prediction_features(session, fixture_id, prediction_cutoff)

    features: JsonDict = {
        **team_result.features_json,
        **xi_result.features_json,
        **market_features,
        **api_features,
        "feature_version": resolved_config.feature_version,
        "prediction_time": prediction_cutoff.isoformat(),
        "target_fixture_id": fixture_id,
        "league_id": target.league_id,
        "season": target.season,
        "home_team_id": target.home_team_id,
        "away_team_id": target.away_team_id,
    }
    data_quality = _global_data_quality(
        team_quality=team_result.data_quality_json,
        xi_quality=xi_result.data_quality_json,
        market_quality=market_quality,
        api_quality=api_quality,
        feature_version=resolved_config.feature_version,
    )
    features["data_quality_score"] = data_quality["data_quality_score"]
    return GlobalFeatureResult(features_json=features, data_quality_json=data_quality)


def _resolve_market_bet_id(
    config: GlobalFeatureConfig,
    api_reference: ApiFootballReference | None,
) -> int | None:
    if config.market_bet_id is not None:
        return config.market_bet_id
    if api_reference is None:
        return None
    try:
        return resolve_1x2_bet_id(api_reference)
    except ReferenceLookupError:
        return None


def _market_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    *,
    bet_id: int | None,
) -> tuple[JsonDict, JsonDict]:
    consensus = compute_market_consensus(
        session,
        fixture_id,
        as_of_time=prediction_time,
        bet_id=bet_id,
    )
    movement = compute_odds_movement(
        session,
        fixture_id,
        prediction_time,
        bet_id=bet_id,
    )
    if consensus is None:
        return (
            {
                "p_market_home": None,
                "p_market_draw": None,
                "p_market_away": None,
                "market_overround": None,
                "market_bookmaker_count": 0,
                "market_dispersion": None,
                "market_confidence": None,
                "market_fetched_at": None,
                "odds_delta_home": movement.delta_home,
                "odds_delta_draw": movement.delta_draw,
                "odds_delta_away": movement.delta_away,
                "odds_first_fetched_at": _iso_or_none(movement.first_fetched_at),
                "odds_latest_fetched_at": _iso_or_none(movement.latest_fetched_at),
            },
            {"odds_available": False, "warnings": ["odds unavailable before prediction_time"]},
        )
    return (
        {
            "p_market_home": consensus.p_market_home,
            "p_market_draw": consensus.p_market_draw,
            "p_market_away": consensus.p_market_away,
            "market_overround": consensus.overround,
            "market_bookmaker_count": consensus.bookmaker_count,
            "market_dispersion": consensus.market_dispersion,
            "market_confidence": consensus.market_confidence,
            "market_fetched_at": consensus.fetched_at.isoformat(),
            "odds_delta_home": movement.delta_home,
            "odds_delta_draw": movement.delta_draw,
            "odds_delta_away": movement.delta_away,
            "odds_first_fetched_at": _iso_or_none(movement.first_fetched_at),
            "odds_latest_fetched_at": _iso_or_none(movement.latest_fetched_at),
        },
        {"odds_available": True, "warnings": []},
    )


def _api_prediction_features(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> tuple[JsonDict, JsonDict]:
    snapshot = session.execute(
        select(models.ApiPredictionSnapshot)
        .where(
            models.ApiPredictionSnapshot.fixture_id == fixture_id,
            models.ApiPredictionSnapshot.fetched_at <= prediction_time,
        )
        .order_by(models.ApiPredictionSnapshot.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if snapshot is None:
        return (
            {
                "p_api_home": None,
                "p_api_draw": None,
                "p_api_away": None,
                "api_prediction_fetched_at": None,
                "api_prediction_winner_team_id": None,
                "api_prediction_advice": None,
            },
            {
                "api_prediction_available": False,
                "warnings": ["api prediction unavailable before prediction_time"],
            },
        )
    return (
        {
            "p_api_home": _normalize_percent(snapshot.percent_home),
            "p_api_draw": _normalize_percent(snapshot.percent_draw),
            "p_api_away": _normalize_percent(snapshot.percent_away),
            "api_prediction_fetched_at": snapshot.fetched_at.isoformat(),
            "api_prediction_winner_team_id": snapshot.winner_team_id,
            "api_prediction_advice": snapshot.advice,
        },
        {"api_prediction_available": True, "warnings": []},
    )


def _global_data_quality(
    *,
    team_quality: JsonDict,
    xi_quality: JsonDict,
    market_quality: JsonDict,
    api_quality: JsonDict,
    feature_version: str,
) -> JsonDict:
    flags = {
        "team_history_available": (
            int(team_quality.get("home_team_history_count") or 0) > 0
            and int(team_quality.get("away_team_history_count") or 0) > 0
        ),
        "odds_available": bool(market_quality.get("odds_available")),
        "lineups_xi_available": (
            int(xi_quality.get("home_team_lineups_available") or 0) > 0
            and int(xi_quality.get("away_team_lineups_available") or 0) > 0
        ),
        "player_stats_available": (
            int(xi_quality.get("home_team_player_stats_available") or 0) > 0
            and int(xi_quality.get("away_team_player_stats_available") or 0) > 0
        ),
        "standings_available": bool(team_quality.get("standings_available")),
        "injuries_available": (
            int(xi_quality.get("home_team_injuries_available") or 0) > 0
            or int(xi_quality.get("away_team_injuries_available") or 0) > 0
        ),
        "api_prediction_available": bool(api_quality.get("api_prediction_available")),
    }
    weights = {
        "team_history_available": 25,
        "odds_available": 20,
        "lineups_xi_available": 15,
        "player_stats_available": 15,
        "standings_available": 10,
        "injuries_available": 5,
        "api_prediction_available": 10,
    }
    warnings = [
        *list(team_quality.get("warnings") or []),
        *list(xi_quality.get("home_team_warnings") or []),
        *list(xi_quality.get("away_team_warnings") or []),
        *list(market_quality.get("warnings") or []),
        *list(api_quality.get("warnings") or []),
    ]
    score = sum(points for flag, points in weights.items() if flags[flag])
    return {
        "feature_version": feature_version,
        "data_quality_score": score,
        **flags,
        "source_versions": {
            "team": team_quality.get("feature_version"),
            "player_xi": xi_quality.get("feature_version"),
        },
        "warnings": warnings,
    }


def _normalize_percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 100 if value > 1 else value


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
