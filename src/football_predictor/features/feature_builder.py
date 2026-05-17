"""Public Sprint 10 feature builder API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db import models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.features.data_quality import feature_quality_payload
from football_predictor.features.draw_risk_features import build_draw_risk_features
from football_predictor.features.lineup_m30_features import build_lineup_m30_features
from football_predictor.features.no_draw_winner_features import build_no_draw_winner_features
from football_predictor.features.odds_features import (
    compute_market_consensus,
    compute_odds_movement,
)
from football_predictor.features.team_features import build_team_features
from football_predictor.features.xi_features import build_player_xi_features
from football_predictor.reference.lookups import ApiFootballReference, PlayersReference
from football_predictor.utils.exceptions import DataQualityError
from football_predictor.utils.time import ensure_aware_utc

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class FeatureBuilderResult:
    snapshot: models.FeatureSnapshot
    features_json: JsonDict
    data_quality_json: JsonDict


def build_feature_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    feature_version: str = "v1",
    players_reference: PlayersReference | None = None,
    api_reference: ApiFootballReference | None = None,
) -> FeatureBuilderResult:
    """Build, store and return a complete point-in-time feature snapshot."""
    session.flush()
    cutoff = ensure_aware_utc(prediction_time)
    fixture = session.get(models.Fixture, fixture_id)
    if fixture is None:
        raise DataQualityError(f"Unknown fixture_id={fixture_id}")

    team_result = build_team_features(session, fixture_id, cutoff)
    xi_result = build_player_xi_features(
        session,
        fixture_id,
        cutoff,
        players_reference=players_reference,
    )
    market = compute_market_consensus(session, fixture_id, cutoff)
    movement = compute_odds_movement(session, fixture_id, cutoff)
    api_prediction = _latest_api_prediction(session, fixture_id, cutoff)

    api_features = _api_prediction_features(api_prediction, fixture)
    features: JsonDict = {
        **team_result.features_json,
        **xi_result.features_json,
        **_market_features(market, movement),
        **api_features,
        "fixture_id": fixture_id,
        "target_fixture_id": fixture_id,
        "league_id": fixture.league_id,
        "season": fixture.season,
        "prediction_time": cutoff.isoformat(),
        "home_team_id": fixture.home_team_id,
        "away_team_id": fixture.away_team_id,
        "feature_version": feature_version,
    }
    if _is_v3_feature_version(feature_version):
        features.update(_v3_feature_payload(session, fixture_id, cutoff, features))
    _remove_target_leakage_fields(features)

    data_quality = _data_quality_payload(
        session=session,
        fixture=fixture,
        prediction_time=cutoff,
        team_quality=team_result.data_quality_json,
        xi_quality=xi_result.data_quality_json,
        odds_available=market is not None,
        api_prediction_available=api_prediction is not None,
        reference_docs_available=players_reference is not None or api_reference is not None,
        feature_version=feature_version,
    )
    if _is_v3_feature_version(feature_version):
        _add_v3_data_quality_flags(
            session=session,
            fixture_id=fixture_id,
            prediction_time=cutoff,
            features=features,
            data_quality=data_quality,
        )
    features["overall_data_quality_score"] = data_quality["overall_data_quality_score"]
    if _is_v3_feature_version(feature_version):
        features["data_quality_score"] = data_quality["overall_data_quality_score"]
        features["has_odds_multi_snapshot"] = int(data_quality["has_odds_multi_snapshot"])
    snapshot = upsert_by_fields(
        session,
        models.FeatureSnapshot,
        {
            "fixture_id": fixture_id,
            "prediction_time": cutoff,
            "feature_version": feature_version,
        },
        {
            "features_json": features,
            "data_quality_json": data_quality,
        },
    )
    session.flush()
    return FeatureBuilderResult(
        snapshot=snapshot,
        features_json=features,
        data_quality_json=data_quality,
    )


def _is_v3_feature_version(feature_version: str) -> bool:
    return feature_version.casefold().startswith("v3")


def _v3_feature_payload(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    base_features: JsonDict,
) -> JsonDict:
    lineup_features = build_lineup_m30_features(session, fixture_id, prediction_time)
    features_with_lineup = {**base_features, **lineup_features}
    draw_risk_features = build_draw_risk_features(
        features_with_lineup,
        session=session,
        fixture_id=fixture_id,
        prediction_time=prediction_time,
    )
    no_draw_winner_features = build_no_draw_winner_features(features_with_lineup)
    official_home = bool(lineup_features.get("official_lineup_home_available_flag"))
    official_away = bool(lineup_features.get("official_lineup_away_available_flag"))
    return {
        **lineup_features,
        **draw_risk_features,
        **no_draw_winner_features,
        "has_official_lineup_home": official_home,
        "has_official_lineup_away": official_away,
        "has_official_lineup": official_home and official_away,
    }


def _add_v3_data_quality_flags(
    *,
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
    features: JsonDict,
    data_quality: JsonDict,
) -> None:
    home_available = bool(features.get("official_lineup_home_available_flag"))
    away_available = bool(features.get("official_lineup_away_available_flag"))
    data_quality.update(
        {
            "has_official_lineup_home": home_available,
            "has_official_lineup_away": away_available,
            "has_official_lineup": home_available and away_available,
            "official_lineup_available_flag": home_available and away_available,
            "has_odds_multi_snapshot": _has_odds_multi_snapshot(
                session, fixture_id, prediction_time
            ),
            "v3_feature_version": features.get("feature_version"),
        }
    )


def _has_odds_multi_snapshot(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> bool:
    rows = session.execute(
        select(models.OddsSnapshot.fetched_at)
        .where(
            models.OddsSnapshot.fixture_id == fixture_id,
            models.OddsSnapshot.is_live.is_(False),
            models.OddsSnapshot.fetched_at <= prediction_time,
            models.OddsSnapshot.odd_home.is_not(None),
            models.OddsSnapshot.odd_draw.is_not(None),
            models.OddsSnapshot.odd_away.is_not(None),
        )
        .distinct()
        .limit(2)
    ).all()
    return len(rows) >= 2


def _latest_api_prediction(
    session: Session,
    fixture_id: int,
    prediction_time: datetime,
) -> models.ApiPredictionSnapshot | None:
    return session.execute(
        select(models.ApiPredictionSnapshot)
        .where(
            models.ApiPredictionSnapshot.fixture_id == fixture_id,
            models.ApiPredictionSnapshot.fetched_at <= prediction_time,
        )
        .order_by(models.ApiPredictionSnapshot.fetched_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _api_prediction_features(
    snapshot: models.ApiPredictionSnapshot | None,
    fixture: models.Fixture,
) -> JsonDict:
    if snapshot is None:
        return {
            "api_pred_home": None,
            "api_pred_draw": None,
            "api_pred_away": None,
            "api_pred_winner_home_flag": False,
            "api_pred_winner_away_flag": False,
            "api_pred_win_or_draw_flag": False,
            "api_pred_fetched_at": None,
        }
    return {
        "api_pred_home": _normalize_percent(snapshot.percent_home),
        "api_pred_draw": _normalize_percent(snapshot.percent_draw),
        "api_pred_away": _normalize_percent(snapshot.percent_away),
        "api_pred_winner_home_flag": snapshot.winner_team_id == fixture.home_team_id,
        "api_pred_winner_away_flag": snapshot.winner_team_id == fixture.away_team_id,
        "api_pred_win_or_draw_flag": bool(snapshot.win_or_draw),
        "api_pred_fetched_at": snapshot.fetched_at.isoformat(),
    }


def _market_features(market: Any, movement: Any) -> JsonDict:
    if market is None:
        return {
            "market_home": None,
            "market_draw": None,
            "market_away": None,
            "market_bookmaker_count": 0,
            "market_confidence": None,
            "market_dispersion": None,
            "odds_movement_home": movement.delta_home,
            "odds_movement_draw": movement.delta_draw,
            "odds_movement_away": movement.delta_away,
        }
    return {
        "market_home": market.p_market_home,
        "market_draw": market.p_market_draw,
        "market_away": market.p_market_away,
        "market_bookmaker_count": market.bookmaker_count,
        "market_confidence": market.market_confidence,
        "market_dispersion": market.market_dispersion,
        "odds_movement_home": movement.delta_home,
        "odds_movement_draw": movement.delta_draw,
        "odds_movement_away": movement.delta_away,
    }


def _data_quality_payload(
    *,
    session: Session,
    fixture: models.Fixture,
    prediction_time: datetime,
    team_quality: JsonDict,
    xi_quality: JsonDict,
    odds_available: bool,
    api_prediction_available: bool,
    reference_docs_available: bool,
    feature_version: str,
) -> JsonDict:
    home_history = int(team_quality.get("home_team_history_count") or 0)
    away_history = int(team_quality.get("away_team_history_count") or 0)
    team_stats_rate = float(team_quality.get("fixture_statistics_coverage_ratio") or 0.0)
    player_stats_home = int(xi_quality.get("home_team_player_stats_available") or 0)
    player_stats_away = int(xi_quality.get("away_team_player_stats_available") or 0)
    lineups_home = int(xi_quality.get("home_team_lineups_available") or 0)
    lineups_away = int(xi_quality.get("away_team_lineups_available") or 0)
    injuries_home = int(xi_quality.get("home_team_injuries_available") or 0)
    injuries_away = int(xi_quality.get("away_team_injuries_available") or 0)
    target_lineups = _target_lineups_availability(session, fixture, prediction_time)
    historical_lineups_available = lineups_home > 0 and lineups_away > 0
    historical_player_stats_rate = (
        (1 if player_stats_home > 0 else 0) + (1 if player_stats_away > 0 else 0)
    ) / 2
    payload = feature_quality_payload(
        historical_matches_home_count=home_history,
        historical_matches_away_count=away_history,
        team_stats_available_rate=team_stats_rate,
        player_stats_available_rate=historical_player_stats_rate,
        lineups_available_flag=(
            target_lineups["target_lineups_available_flag"] or historical_lineups_available
        ),
        injuries_available_flag=injuries_home > 0 or injuries_away > 0,
        odds_available_flag=odds_available,
        api_prediction_available_flag=api_prediction_available,
        reference_docs_available_flag=reference_docs_available,
        standings_available_flag=bool(team_quality.get("standings_available")),
        warnings=[
            *list(team_quality.get("warnings") or []),
            *list(xi_quality.get("home_team_warnings") or []),
            *list(xi_quality.get("away_team_warnings") or []),
        ],
    )
    payload.update(
        {
            **target_lineups,
            "historical_lineups_available_flag": historical_lineups_available,
            "historical_lineups_home_available_flag": lineups_home > 0,
            "historical_lineups_away_available_flag": lineups_away > 0,
            "historical_player_stats_available_rate": historical_player_stats_rate,
            "historical_player_stats_home_available_flag": player_stats_home > 0,
            "historical_player_stats_away_available_flag": player_stats_away > 0,
        }
    )
    payload["feature_version"] = feature_version
    return payload


def _target_lineups_availability(
    session: Session,
    fixture: models.Fixture,
    prediction_time: datetime,
) -> JsonDict:
    team_ids = {
        "home": fixture.home_team_id,
        "away": fixture.away_team_id,
    }
    rows = session.execute(
        select(models.FixtureLineup).where(
            models.FixtureLineup.fixture_id == fixture.fixture_id,
            models.FixtureLineup.team_id.in_(
                [team_id for team_id in team_ids.values() if team_id is not None]
            ),
            models.FixtureLineup.fetched_at <= prediction_time,
        )
    ).scalars()
    available_team_ids = {row.team_id for row in rows}
    home_available = (
        fixture.home_team_id is not None and fixture.home_team_id in available_team_ids
    )
    away_available = (
        fixture.away_team_id is not None and fixture.away_team_id in available_team_ids
    )
    return {
        "target_lineups_home_available_flag": home_available,
        "target_lineups_away_available_flag": away_available,
        "target_lineups_available_flag": home_available and away_available,
    }


def _normalize_percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 100 if value > 1 else value


def _remove_target_leakage_fields(features: JsonDict) -> None:
    for key in ("target", "home_goals", "away_goals", "goals_home", "goals_away"):
        features.pop(key, None)
